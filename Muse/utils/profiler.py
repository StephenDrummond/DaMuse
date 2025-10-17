from dataclasses import dataclass
from datetime import datetime
from typing import List, Dict, Any

import discord
import asyncio

from .db_client import DBClient
from api.spotify import get_spotify_info


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
    def __init__(self, db):
        super().__init__(db)

    # Map preference tables to the target table and column for fetching the id
    TABLE_KEY_MAPPING = {
        "song_user_likes": ("songs", "title", "song_id"),
        "artist_user_likes": ("artists", "name", "artist_id"),
        "genre_user_likes": ("genres", "name", "genre_id"),
    }

    async def log_event(
        self, member: discord.Member, song: str, alpha: float, liked: bool
    ) -> None:
        """Generic event logger for plays, likes, skips, and dislikes."""
        member_id = member.id
        info = await get_spotify_info(song)
        song_info = SongInfo(
            name=info["name"],
            artists=info["artists"],
            genres=info.get("genres", []),
        )
        # after meta data is gathered and formatted log all the different preference changes
        await self._log_preference_group(member_id, song_info, alpha, liked)

    async def _log_preference_group(
        self, member_id: int, song_info: SongInfo, alpha: float, liked: bool
    ) -> None:
        """Logs song, artist, and genre preferences concurrently."""
        tasks = [
            self.log_preference(
                "song_user_likes", song_info.name, member_id, alpha, liked
            ),
            self.log_preference(
                "artist_user_likes", song_info.artists[0], member_id, alpha, liked
            ),
        ]

        # Add genre tasks (generator expression)
        tasks.extend(
            self.log_preference("genre_user_likes", genre, member_id, alpha, liked)
            for genre in song_info.genres
        )

        # Run all tasks concurrently
        await asyncio.gather(*tasks)

    async def log_preference(
        self,
        table_name: str,
        target_name: str,
        member_id: int,
        alpha: float,
        liked: bool,
    ) -> None:
        """
        Helper to insert or update a preference record.
        """
        target_table, lookup_column, pref_table_column = self.TABLE_KEY_MAPPING[
            table_name
        ]

        # Fetch the target id from the correct table
        target_id: int = await self.db.fetch_val(
            f"SELECT id FROM {target_table} WHERE {lookup_column} = $1",
            target_name,
        )

        # Use the correct column in the preference table
        await self.upsert_preference_in_db(
            table_name=table_name,
            user_id=member_id,
            target_id=target_id,
            liked_at=datetime.today(),
            target_column=pref_table_column,
            alpha=alpha,
            liked=liked,
        )

    async def upsert_preference_in_db(
        self,
        table_name: str,
        user_id: int,
        target_id: int,
        liked_at: datetime,
        target_column: str,
        alpha: float,
        liked: bool,
        base_preference_score: float = 0.5,
    ) -> None:
        """Insert or update a like record in the database."""
        await self.upsert_preferences(
            table_name,
            ["user_id", target_column],
            ["liked_at", "preference_score", "liked"],
            user_id,
            target_id,
            liked_at,
            alpha,
            liked,
        )


# -------------------------
# Example usage / testing
# -------------------------
if __name__ == "__main__":
    import asyncio

    # Optional helper constants for common events
    EVENTS = {
        "play": {"alpha": 0.2, "liked": True},
        "like": {"alpha": 0.4, "liked": True},
        "dislike": {"alpha": -0.5, "liked": False},
        "skip": {"alpha": -0.2, "liked": False},
    }

    async def main():
        profiler = Profiler()
        await profiler.create_db()

        # Fake Discord members for testing
        class FakeMember:
            def __init__(self, id: int):
                self.id = id

        members = [FakeMember(62), FakeMember(64), FakeMember(56)]
        test_songs = ["Money Pink Floyd", "Rockafeller skank", "Charleston girl"]

        tasks = [
            profiler.log_event(call[0], call[1], **EVENTS[call[2]])
            for call in [
                (members[1], test_songs[0], "skip"),
            ]
        ]

        # Run all tasks concurrently
        await asyncio.gather(*tasks)
        print("Events logged successfully.")

    asyncio.run(main())
