"""Grows the song registry with known artists' Spotify top tracks.

The Curator can only pick songs that are in the `songs` table, which used to
mean songs someone had already played. Seeding adds each known artist's most
popular tracks, so a liked artist brings songs the room hasn't heard yet.
Runs in worker.py, never on the bot's playback path.
"""

import asyncio
import logging
from dataclasses import dataclass
from typing import Optional

from clients.spotify import SpotifyClient
from db.client import DBClient
from taste.librarian import Librarian

logger = logging.getLogger(__name__)

SEED_INTERVAL_SECONDS = 300  # how often to look for artists to seed
BACKLOG_PAUSE_SECONDS = 5  # between rounds while a backlog remains
ARTISTS_PER_ROUND = 5  # ~2 Spotify calls each; keeps well under rate limits
RESEED_AFTER_DAYS = 30  # top tracks change; refresh each artist monthly
MARKET = "US"  # top tracks are per country


@dataclass(frozen=True)
class SeedArtist:
    id: int
    name: str
    spotify_id: Optional[str]


@dataclass(frozen=True)
class SimilarArtist:
    """An artist named in `!switch <artist>`, ready for the Curator."""

    artist_id: int
    name: str
    genre_ids: list[int]


class Seeder(DBClient):
    def __init__(self, db, spotify: SpotifyClient, librarian: Librarian):
        super().__init__(db)
        self.spotify = spotify
        self.librarian = librarian

    async def claim_artists(self, limit: int = ARTISTS_PER_ROUND) -> list[SeedArtist]:
        """Take up to `limit` artists never seeded (first) or not seeded in
        RESEED_AFTER_DAYS, stamping seeded_at so other workers skip them."""
        rows = await self.db.fetch(
            """
            UPDATE artists SET seeded_at = now()
            WHERE id IN (
                SELECT id FROM artists
                WHERE seeded_at IS NULL
                   OR seeded_at < now() - make_interval(days => $2)
                ORDER BY seeded_at NULLS FIRST, id
                FOR UPDATE SKIP LOCKED
                LIMIT $1
            )
            RETURNING id, name, spotify_id
            """,
            limit,
            RESEED_AFTER_DAYS,
        )
        return [
            SeedArtist(id=r["id"], name=r["name"], spotify_id=r["spotify_id"])
            for r in rows
        ]

    async def prepare_artist(self, name: str) -> Optional[SimilarArtist]:
        """Find `name` on Spotify, register the artist and their genres, and
        add their top tracks now (unless seeded within RESEED_AFTER_DAYS), so
        there's something to play even for an artist nobody has played.
        None if Spotify has no such artist."""
        info = await self.spotify.find_artist(name)
        if info is None:
            return None

        existing = await self.librarian.find_artist(info["name"], info["id"])
        stored_name = existing[1] if existing else info["name"]
        artist_id, genre_ids = await self.librarian.register_artist(
            stored_name, info["genres"], info["id"]
        )

        seeded_recently = await self.db.fetch_val(
            """
            SELECT seeded_at > now() - make_interval(days => $2)
            FROM artists WHERE id = $1
            """,
            artist_id,
            RESEED_AFTER_DAYS,
        )
        if not seeded_recently:
            added = await self.seed_artist(
                SeedArtist(id=artist_id, name=stored_name, spotify_id=info["id"]),
                info,
            )
            await self.db.execute(
                "UPDATE artists SET seeded_at = now() WHERE id = $1", artist_id
            )
            logger.info("Seeded %r for !switch: %d new song(s)", stored_name, added)

        return SimilarArtist(artist_id=artist_id, name=stored_name, genre_ids=genre_ids)

    async def seed_artist(self, artist: SeedArtist, info: Optional[dict] = None) -> int:
        """Register `artist`'s top tracks; returns how many songs were new.

        Only tracks where this artist is the main artist are added, so a
        feature on someone else's hit doesn't drag in a new artist. Songs are
        registered under our stored name, so a different capitalization on
        Spotify can't create a duplicate artist.
        """
        if info is None:  # not already looked up by the caller
            info = (
                await self.spotify.get_artist(artist.spotify_id)
                if artist.spotify_id
                else await self.spotify.find_artist(artist.name)
            )
        if info is None:
            logger.info(
                "No Spotify artist for %r; retrying in %d days",
                artist.name,
                RESEED_AFTER_DAYS,
            )
            return 0
        if not artist.spotify_id:
            await self.db.execute(
                """
                UPDATE artists SET spotify_id = $2
                WHERE id = $1 AND spotify_id IS NULL
                """,
                artist.id,
                info["id"],
            )

        tracks = await self.spotify.artist_top_tracks(info["id"], MARKET)
        before = await self._song_count(artist.id)
        for track in tracks:
            if not track["artist_ids"] or track["artist_ids"][0] != info["id"]:
                continue
            await self.librarian.register_track(
                track["name"],
                artist.name,
                info["genres"],
                spotify_track_id=track["id"],
                spotify_artist_id=info["id"],
                source="top_tracks",
            )
        return await self._song_count(artist.id) - before

    async def seed_round(self, limit: int = ARTISTS_PER_ROUND) -> int:
        """Seed one batch of artists; returns how many were claimed."""
        artists = await self.claim_artists(limit)
        for artist in artists:
            try:
                added = await self.seed_artist(artist)
                logger.info("Seeded %r: %d new song(s)", artist.name, added)
            except Exception:
                logger.exception("Seeding %r failed; will retry", artist.name)
                # un-claim so it's picked up again next round
                await self.db.execute(
                    "UPDATE artists SET seeded_at = NULL WHERE id = $1", artist.id
                )
        return len(artists)

    async def run_forever(self) -> None:
        """Seed in batches: quickly while there's a backlog, then every
        SEED_INTERVAL_SECONDS to pick up newly played artists."""
        while True:
            try:
                claimed = await self.seed_round()
            except Exception:
                logger.exception("Seeding round failed")
                claimed = 0
            await asyncio.sleep(
                BACKLOG_PAUSE_SECONDS
                if claimed == ARTISTS_PER_ROUND
                else SEED_INTERVAL_SECONDS
            )

    async def _song_count(self, artist_id: int) -> int:
        count = await self.db.fetch_val(
            "SELECT count(*) FROM songs WHERE artist_id = $1", artist_id
        )
        return int(count or 0)
