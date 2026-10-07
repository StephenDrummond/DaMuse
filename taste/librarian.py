from dataclasses import dataclass
from typing import Optional

from db.db import Database
from db.client import DBClient


@dataclass(frozen=True)
class TrackIds:
    song_id: int
    artist_id: int
    genre_ids: list[int]


class Librarian(DBClient):
    """Keeps the users / artists / songs / genres lookup tables populated."""

    def __init__(self, db: Database):
        super().__init__(db)

    async def add_member_to_db(self, member_id: int, member_name: str):
        if type(member_id) is not int:
            raise TypeError("member_id must be an int")

        await self.insert_if_not_exists(
            "users", ["discord_id", "username"], member_id, member_name
        )

    async def add_members_to_db(self, members: list[tuple[int, str]]):
        """Batch version of add_member_to_db: one round trip for many members."""
        if not members:
            return
        await self.db.batch_insert(
            """
            INSERT INTO users (discord_id, username) VALUES ($1, $2)
            ON CONFLICT (discord_id) DO NOTHING
            """,
            members,
        )

    async def register_track(
        self,
        title: str,
        artist: str,
        genres: list[str],
        spotify_track_id: Optional[str] = None,
        spotify_artist_id: Optional[str] = None,
        source: str = "played",
    ) -> TrackIds:
        """Insert the song, its (primary) artist and the artist's genres if they
        don't exist yet, link artist <-> genres, and return all their ids.

        Spotify ids fill in rows that don't have one yet but never replace one.
        `source` records how a *new* song got here ('played' or 'top_tracks');
        an existing song keeps its original source.

        The `DO UPDATE` (rather than `DO NOTHING`) is what makes `RETURNING id`
        yield the existing row's id on conflict.
        """
        if type(title) is not str or type(artist) is not str:
            raise TypeError("title and artist must be str")

        async with self.db.transaction() as conn:
            artist_id, genre_ids = await self._upsert_artist(
                conn, artist, genres, spotify_artist_id
            )
            song_id = await conn.fetchval(
                """
                INSERT INTO songs (title, artist_id, spotify_id, source)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (title, artist_id) DO UPDATE
                SET spotify_id = COALESCE(songs.spotify_id, EXCLUDED.spotify_id)
                RETURNING id
                """,
                title,
                artist_id,
                spotify_track_id,
                source,
            )

        return TrackIds(song_id=song_id, artist_id=artist_id, genre_ids=genre_ids)

    async def register_artist(
        self,
        name: str,
        genres: list[str],
        spotify_artist_id: Optional[str] = None,
    ) -> tuple[int, list[int]]:
        """Insert the artist and their genres if missing, link them, and
        return (artist id, genre ids). For artists known before any of their
        songs, e.g. one named in !switch."""
        async with self.db.transaction() as conn:
            return await self._upsert_artist(conn, name, genres, spotify_artist_id)

    async def find_artist(
        self, name: str, spotify_artist_id: Optional[str] = None
    ) -> Optional[tuple[int, str]]:
        """(id, stored name) of an existing artist matching the Spotify id, or
        the name ignoring case, so a differently capitalized name isn't
        registered twice."""
        row = await self.db.fetch_row(
            """
            SELECT id, name FROM artists
            WHERE ($2::varchar IS NOT NULL AND spotify_id = $2)
               OR lower(name) = lower($1)
            ORDER BY spotify_id = $2 DESC NULLS LAST
            LIMIT 1
            """,
            name,
            spotify_artist_id,
        )
        return (row["id"], row["name"]) if row is not None else None

    @staticmethod
    async def _upsert_artist(
        conn, name: str, genres: list[str], spotify_artist_id: Optional[str]
    ) -> tuple[int, list[int]]:
        """Shared by register_track and register_artist; runs inside the
        caller's transaction. Spotify ids fill in, never replace."""
        genres = list(dict.fromkeys(genres))  # de-dupe, keep order
        artist_id = await conn.fetchval(
            """
            INSERT INTO artists (name, spotify_id) VALUES ($1, $2)
            ON CONFLICT (name) DO UPDATE
            SET spotify_id = COALESCE(artists.spotify_id, EXCLUDED.spotify_id)
            RETURNING id
            """,
            name,
            spotify_artist_id,
        )

        genre_ids: list[int] = []
        if genres:
            rows = await conn.fetch(
                """
                INSERT INTO genres (name) SELECT unnest($1::varchar[])
                ON CONFLICT (name) DO UPDATE SET name = EXCLUDED.name
                RETURNING id
                """,
                genres,
            )
            genre_ids = [row["id"] for row in rows]
            await conn.execute(
                """
                INSERT INTO artist_genres (artist_id, genre_id)
                SELECT $1, unnest($2::int[])
                ON CONFLICT DO NOTHING
                """,
                artist_id,
                genre_ids,
            )
        return artist_id, genre_ids

    async def get_track_ids(self, song_id: int) -> TrackIds | None:
        """Look up the artist and genre ids for an already-registered song."""
        row = await self.db.fetch_row(
            """
            SELECT s.id AS song_id, s.artist_id,
                   ARRAY(SELECT genre_id FROM artist_genres
                         WHERE artist_id = s.artist_id) AS genre_ids
            FROM songs s WHERE s.id = $1
            """,
            song_id,
        )
        if row is None:
            return None
        return TrackIds(
            song_id=row["song_id"],
            artist_id=row["artist_id"],
            genre_ids=list(row["genre_ids"]),
        )
