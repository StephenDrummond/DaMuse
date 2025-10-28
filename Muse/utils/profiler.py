import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import List

import discord
import redis

from db.db import Database
from api.spotify import search_track
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
        self.r = redis.from_url("redis://localhost")

    # Map preference tables to target table/column for fetching IDs
    TABLE_KEY_MAPPING = {
        "song_user_likes": ("songs", "name", "song_id"),
        "artist_user_likes": ("artists", "name", "artist_id"),
        "genre_user_likes": ("genres", "name", "genre_id"),
    }

    async def log_event(
        self, member: discord.Member, song: str, alpha: float, liked: bool
    ) -> None:
        """Log a user interaction (play, like, skip, etc.) for a song."""
        info = await search_track(song)
        if info is None:
            return
        
        print(info["type"])

        song_info = SongInfo(
            name=info["name"],
            artists=info["artists"],
            genres=info.get("genres", []),
        )
        await self._log_preference_group(member.id, song_info, alpha, liked)

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
        tasks.extend(
            self.log_preference("genre_user_likes", genre, member_id, alpha, liked)
            for genre in song_info.genres
        )
        await asyncio.gather(*tasks)

    async def log_preference(
        self,
        table_name: str,
        target_name: str,
        member_id: int,
        alpha: float,
        liked: bool,
    ) -> None:
        target_table, lookup_column, table_id = self.TABLE_KEY_MAPPING[table_name]
        try:
            target_id = await self.get_target_id(
                target_table, lookup_column, target_name
            )
            await self.safe_upsert_preference(
                table_name,
                ["user_id", table_id],
                ["liked_at", "preference_score", "liked"],
                member_id,
                target_id,
                datetime.today(),
                alpha,
                liked,
            )
        except ValueError as e:
            logger.warning(e)


async def main():
    db = Database()
    db.init_pool
    await db.init_pool()

    print("prep")
    profiler = Profiler(db)

    print("p")
    class MockMember:
        id = 283796442437517313

    member = MockMember()

    # Example: Log a test event
    song_name = "Blinding Lights"
    alpha = 0.4
    liked = True

    await profiler.log_event(member, song_name, alpha, liked)

    print("Logged preference event successfully.")

# Run
if __name__ == "__main__":
    asyncio.run(main())