import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import List

import discord

from api.spotify import get_spotify_info
from .db_client import DBClient

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


@dataclass
class SongInfo:
    name: str
    artists: List[str]
    genres: List[str]


@dataclass
class PreferenceTarget:
    table_name: str
    column_name: str
    value: str


class Profiler(DBClient):
    """Handles profiling logic; main entry is log_event()."""

    def __init__(self, db):
        super().__init__(db)

    # Map preference tables to target table/column for fetching IDs
    TABLE_KEY_MAPPING = {
        "song_user_likes": ("songs", "name", "song_id"),
        "artist_user_likes": ("artists", "name", "artist_id"),
        "genre_user_likes": ("genres", "name", "genre_id"),
    }

    async def log_event(
        self, member: discord.Member, song: str, alpha: float, liked: bool
    ) -> None:
        """Log a user interaction (play, like, skip, etc) for a song."""
        member_id = member.id

        info = await get_spotify_info(song)
        if info is None:
            return

        song_info = SongInfo(
            name=info["name"],
            artists=info["artists"],
            genres=info.get("genres", []),
        )
        # Log preferences for song, artist, and genres
        await self._log_preference_group(member_id, song_info, alpha, liked)

    async def _log_preference_group(
        self, member_id: int, song_info: SongInfo, alpha: float, liked: bool
    ) -> None:
        """Log song, artist, and genre preferences concurrently."""
        tasks = [
            self.log_preference(
                "song_user_likes", song_info.name, member_id, alpha, liked
            ),
            self.log_preference(
                "artist_user_likes", song_info.artists[0], member_id, alpha, liked
            ),
        ]
        # Add genre tasks
        tasks.extend(
            self.log_preference("genre_user_likes", genre, member_id, alpha, liked)
            for genre in song_info.genres
        )
        # Run all database operations concurrently
        await asyncio.gather(*tasks)

    async def log_preference(
        self,
        table_name: str,
        target_name: str,
        member_id: int,
        alpha: float,
        liked: bool,
    ) -> None:
        """Fetch target ID and upsert preference in the DB."""
        target_table, lookup_column, table_id = self.TABLE_KEY_MAPPING[table_name]

        try:
            # Get the ID of the song/artist/genre
            target_id: int | None = await self.db.fetch_val(
                f"SELECT id FROM {target_table} WHERE {lookup_column} = $1",
                target_name,
            )

            if target_id is None:
                raise ValueError(
                    f"\nNo target_id found for {target_name} in {target_table}"
                )

            # Upsert the like/preference record
            await self.upsert_preference_in_db(
                table_name=table_name,
                user_id=member_id,
                target_id=target_id,
                liked_at=datetime.today(),
                foreign_table_id=table_id,
                alpha=alpha,
                liked=liked,
            )
        except ValueError as e:
            logger.exception(e)
            # Should maybe find a way to check if the song exists and
            # insert it if it does?? could be redundant.
        except Exception as e:
            # Log or handle the error however you want
            logger.exception(
                f"\nError logging preference: {e} \n"
                f"Could not log {table_name} {target_name} for user: {member_id}"
            )

    async def upsert_preference_in_db(
        self,
        table_name: str,
        user_id: int,
        target_id: int,
        liked_at: datetime,
        foreign_table_id: str,
        alpha: float,
        liked: bool,
        base_preference_score: float = 0.5,
    ) -> None:
        """Insert or update a like record in the database."""
        await self.upsert_preference(
            table_name,
            ["user_id", foreign_table_id],
            ["liked_at", "preference_score", "liked"],
            user_id,
            target_id,
            liked_at,
            alpha,
            liked,
        )
