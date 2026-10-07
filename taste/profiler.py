import logging
from dataclasses import dataclass
from typing import Optional

from clients.spotify import SpotifyClient
from taste.librarian import Librarian, TrackIds
from db.client import DBClient

logger = logging.getLogger(__name__)

# event type -> (target score, learning rate). Each event nudges the listener's
# song/artist/genre scores `rate` of the way toward `target` (see
# DBClient.build_score_update_query). Passive signals move scores a little,
# explicit ones a lot.
EVENT_SIGNALS: dict[str, tuple[float, float]] = {
    "listen": (1.0, 0.05),  # was in the room when the song finished
    "skip": (0.0, 0.15),  # !skip
    "like": (1.0, 0.3),  # !like
    "dislike": (0.0, 0.3),  # !dislike
}

# How much of an event's rate reaches the song's artist and genres (default: all
# of it). A skip says "not this song, not now" far more than it says anything
# about the artist, and genres are shared by many artists, so one skip
# shouldn't drag down everything else in the genre.
LEVEL_RATE_FACTORS: dict[str, dict[str, float]] = {
    "skip": {"artist": 1 / 3, "genre": 0.2},  # 0.15 -> artist 0.05, genre 0.03
}

LEVEL_TABLES: dict[str, str] = {
    "song": "song_user_likes",
    "artist": "artist_user_likes",
    "genre": "genre_user_likes",
}


def level_rate(event_type: str, level: str) -> float:
    """The learning rate `event_type` applies at `level` (song/artist/genre)."""
    _, rate = EVENT_SIGNALS[event_type]
    return rate * LEVEL_RATE_FACTORS.get(event_type, {}).get(level, 1.0)


@dataclass(frozen=True)
class PlayRecord:
    play_id: int
    track: TrackIds


class Profiler(DBClient):
    """Write path for listening history: records plays and listener events in
    Postgres and folds each event into the preference scores, all in the same
    transaction. Postgres is the only store, so there's nothing to sync back."""

    def __init__(self, db, spotify: SpotifyClient, librarian: Librarian):
        super().__init__(db)
        self.spotify = spotify
        self.librarian = librarian

    @staticmethod
    def lookup_key(title: str, artist: Optional[str]) -> str:
        return f"{(artist or '').strip().lower()}|{title.strip().lower()}"

    async def resolve_track(
        self, title: str, artist: Optional[str]
    ) -> Optional[TrackIds]:
        """Map a (title, artist) hint to registered song/artist/genre ids,
        consulting the track_lookups cache before Spotify."""
        key = self.lookup_key(title, artist)
        cached = await self.db.fetch_row(
            """
            SELECT tl.song_id, s.artist_id,
                   ARRAY(SELECT genre_id FROM artist_genres
                         WHERE artist_id = s.artist_id) AS genre_ids,
                   tl.looked_up_at > now() - interval '1 day' AS fresh
            FROM track_lookups tl
            LEFT JOIN songs s ON s.id = tl.song_id
            WHERE tl.query = $1
            """,
            key,
        )
        if cached is not None:
            if cached["song_id"] is not None:
                return TrackIds(
                    song_id=cached["song_id"],
                    artist_id=cached["artist_id"],
                    genre_ids=list(cached["genre_ids"]),
                )
            if cached["fresh"]:
                return None  # Spotify had no match recently; don't ask again yet

        try:
            info = await self.spotify.search_track(title, artist)
            if info is None and artist:
                # the artist hint is often a channel name; retry on title alone
                info = await self.spotify.search_track(title)
        except Exception:
            logger.exception("Spotify lookup failed for %r", key)
            return None  # transient: not cached, retried next play

        track = None
        if info and info.get("artists"):
            track = await self.librarian.register_track(
                info["name"], info["artists"][0], info.get("genres", [])
            )

        await self.db.execute(
            """
            INSERT INTO track_lookups (query, song_id, looked_up_at)
            VALUES ($1, $2, now())
            ON CONFLICT (query) DO UPDATE
            SET song_id = EXCLUDED.song_id, looked_up_at = EXCLUDED.looked_up_at
            """,
            key,
            track.song_id if track else None,
        )
        return track

    async def record_play(
        self,
        guild_id: int,
        channel_id: int,
        title: str,
        artist: Optional[str],
        requested_by: Optional[int],
        song_id: Optional[int] = None,
    ) -> Optional[PlayRecord]:
        """Insert a `plays` row for a song that just started. Pass `song_id`
        when the song is already known (Curator picks) to skip the lookup.
        Returns None if the song can't be identified on Spotify."""
        if song_id is not None:
            track = await self.librarian.get_track_ids(song_id)
        else:
            track = await self.resolve_track(title, artist)
        if track is None:
            logger.info(
                "No Spotify match for %r by %r; play not recorded", title, artist
            )
            return None

        async with self.db.transaction() as conn:
            if requested_by is not None:
                await self._ensure_users(conn, [requested_by])
            play_id = await conn.fetchval(
                """
                INSERT INTO plays (song_id, guild_id, channel_id, requested_by)
                VALUES ($1, $2, $3, $4)
                RETURNING id
                """,
                track.song_id,
                guild_id,
                channel_id,
                requested_by,
            )
        return PlayRecord(play_id=play_id, track=track)

    async def log_event(
        self, play: PlayRecord, user_ids: list[int], event_type: str
    ) -> None:
        """Record `event_type` for each user on `play` and update their song,
        artist and genre scores in one transaction."""
        if event_type not in EVENT_SIGNALS:
            raise ValueError(f"Unknown event type: {event_type}")
        target, _ = EVENT_SIGNALS[event_type]

        # sorted + unique: an upsert can't touch the same row twice, and a
        # consistent row order keeps concurrent transactions from deadlocking
        users = sorted(set(user_ids))
        if not users:
            return
        items = {
            "song": [play.track.song_id],
            "artist": [play.track.artist_id],
            "genre": sorted(set(play.track.genre_ids)),
        }

        async with self.db.transaction() as conn:
            await self._ensure_users(conn, users)
            await conn.execute(
                """
                INSERT INTO play_events (play_id, user_id, event_type)
                SELECT $1, unnest($2::bigint[]), $3
                """,
                play.play_id,
                users,
                event_type,
            )
            for level, item_ids in items.items():
                if item_ids:
                    await conn.execute(
                        self.build_score_update_query(LEVEL_TABLES[level]),
                        users,
                        item_ids,
                        level_rate(event_type, level),
                        target,
                    )

    @staticmethod
    async def _ensure_users(conn, user_ids: list[int]) -> None:
        """Make sure the FK targets exist. Usernames are filled in by
        ChannelEvents; this only guards against a member it hasn't seen yet."""
        await conn.execute(
            """
            INSERT INTO users (discord_id) SELECT unnest($1::bigint[])
            ON CONFLICT (discord_id) DO NOTHING
            """,
            user_ids,
        )
