from dataclasses import dataclass
from datetime import datetime
from typing import List, Dict, Any

import discord

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
    def __init__(self):
        super().__init__()

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
        info_dict = await get_spotify_info(song)
        song_info = SongInfo(
            name=info_dict["name"],
            artists=info_dict["artists"],
            genres=info_dict.get("genres", []),
        )
        await self._log_preference_group(member_id, song_info, alpha, liked)

    async def _log_preference_group(
        self, member_id: int, song_info: SongInfo, alpha: float, liked: bool
    ) -> None:
        """Logs song, artist, and genre preferences."""
        # Song
        await self.log_preference(
            "song_user_likes", song_info.name, member_id, alpha, liked
        )
        # Artist
        await self.log_preference(
            "artist_user_likes", song_info.artists[0], member_id, alpha, liked
        )
        # Genres
        for genre in song_info.genres:
            await self.log_preference(
                "genre_user_likes", genre, member_id, alpha, liked
            )

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
        await self.upsert(
            table_name,
            ["user_id", target_column],
            ["liked_at", "preference_score", "liked"],
            user_id,
            target_id,
            liked_at,
            base_preference_score + alpha,
            liked,
        )


# Optional helper constants for common events
EVENTS = {
    "play": {"alpha": 0.2, "liked": True},
    "like": {"alpha": 0.4, "liked": True},
    "dislike": {"alpha": -0.5, "liked": False},
    "skip": {"alpha": -0.2, "liked": False},
}

# -------------------------
# Example usage / testing
# -------------------------
if __name__ == "__main__":
    import asyncio

    async def main():
        profiler = Profiler()
        await profiler.create_db()

        # Fake Discord members for testing
        class FakeMember:
            def __init__(self, id: int):
                self.id = id

        members = [FakeMember(62), FakeMember(64), FakeMember(56)]
        test_songs = ["Money Pink Floyd", "Rockafeller skank", "Charleston girl"]

        # Log some events
        for call in [
            (members[0], test_songs[0], "play"),
            (members[1], test_songs[1], "play"),
            (members[0], test_songs[1], "like"),
            (members[2], test_songs[1], "like"),
            (members[0], test_songs[2], "skip"),
        ]:
            asyncio.create_task(profiler.log_event(call[0], call[1], **EVENTS[call[2]]))

        print("Events logged successfully.")

    asyncio.run(main())
