from datetime import datetime
from typing import Any

import discord

from db.db import Database
from utils.spotify import get_spotify_info


class Profiler(object):
    def __init__(self):
        self.db = Database()

    async def create_db(self):
        await self.db.init_pool()

    async def log_preference(self, table_name: str,
                             target_column: str,
                             target_name: str,
                             member_id: int,
                             alpha: float,
                             liked: bool) -> None:
        """
        Helper to insert or update a preference record.
        """
        # SQL query that changes based on the column names in the tables (artists and genres = name | songs = title)
        target_id: int = await self.db.fetch_val(
            f"SELECT id FROM {table_name.replace('_user_likes', 's')} WHERE name = $1" if "artist" in target_column or "genre" in target_column
            else "SELECT id FROM songs WHERE title = $1",
            target_name
        )
        await self.upsert_preference_in_db(
            table_name=table_name,
            user_id=member_id,
            target_id=target_id,
            liked_at=datetime.today(),
            target_column=target_column,
            alpha=alpha,
            liked=liked
        )

    async def _log_preference_group(
            self,
            member_id: int,
            song_info: dict[str, Any],
            alpha: float,
            liked: bool,
    ) -> None:
        """Helper to log song, artist, and genre preferences in one go."""
        # get song metadata
        song_name: str = song_info["name"]
        artist_name: str = song_info["artists"][0]
        genres: list[str] = song_info.get("genres", [])

        # Log song preference
        await self.log_preference("song_user_likes", "song_id", song_name, member_id, alpha, liked)

        # Log artist preference
        await self.log_preference("artist_user_likes", "artist_id", artist_name, member_id, alpha, liked)

        # Log genre preferences
        for genre in genres:
            await self.log_preference("genre_user_likes", "genre_id", genre, member_id, alpha, liked)

    async def _handle_behavioural_event(
            self,
            member: discord.Member,
            song: str,
            alpha: float,
            liked: bool,
    ) -> None:
        """Internal handler that fetches metadata and delegates to _log_preference_group."""
        member_id: int = member.id  # get who interacted with the songs id
        info: dict[str, Any] = await get_spotify_info(song)  # get the song that was interacted with
        await self._log_preference_group(member_id, info, alpha, liked)

    async def upsert_preference_in_db(
            self,
            table_name: str,
            user_id: int,
            target_id: int,
            liked_at: datetime,
            target_column: str,
            alpha: float,
            liked: bool,
            base_preference_score=0.5
    ) -> None:
        """
        Inserts a like record into a table, or updates it on conflict.

        Args:
            table_name: Name of the table (e.g., "song_user_likes").
            user_id: ID of the user.
            target_id: ID of the song or artist.
            liked_at: Timestamp of the like.
            target_column: The column name for the target ID (e.g., "song_id", "artist_id").
            alpha: The increment by which preference score is updated by.
            liked: Whether the user likes or dislikes this song
            base_preference_score: the basis for a whether a user likes or dislikes a song
        """

        query = f"""
            INSERT INTO {table_name} (user_id, {target_column}, liked_at, preference_score, liked)
            VALUES ($1, $2, $3, $4, $5)
            ON CONFLICT (user_id, {target_column}) DO UPDATE
            SET preference_score = GREATEST(LEAST({table_name}.preference_score + {alpha}, 1.0), 0.0),
                liked = $5,
                liked_at = $3;
        """
        await self.db.execute(query, user_id, target_id, liked_at, base_preference_score + alpha, liked)

    async def log_user_play_event(self, member: discord.Member, song: str) -> None:
        """User played a song."""
        await self._handle_behavioural_event(member, song, alpha=0.2, liked=True)

    async def log_user_like_song(self, member: discord.Member, song: str) -> None:
        """User liked a song."""
        await self._handle_behavioural_event(member, song, alpha=0.4, liked=True)

    async def log_user_dislike_song(self, member: discord.Member, song: str, ) -> None:
        """User disliked a song."""
        await self._handle_behavioural_event(member, song, alpha=-0.5, liked=False)

    async def log_user_skip_song(self, member: discord.Member, song: str) -> None:
        """User skipped a song."""
        await self._handle_behavioural_event(member, song, alpha=-0.2, liked=True)

    async def log_user_listened_to(self, member: discord.Member, song: str, alpha: float = 0.1) -> None:
        """User listened to a song without skipping."""


if __name__ == "__main__":
    import asyncio


    async def main():
        profiler = Profiler()
        await profiler.create_db()

        # Fake Discord member for testing
        class FakeMember:
            id: int

            def __init__(self, num):
                self.id = num

        member1 = FakeMember(62)
        member2 = FakeMember(64)
        member3 = FakeMember(56)

        # Test song name
        test_song1 = "Money Pink Floyd"
        test_song2 = "Rockafeller skank"
        test_song3 = "Charleston girl"

        print(f"Logging play event for song: {test_song1}")
        await profiler.log_user_play_event(member1, test_song1)
        await profiler.log_user_play_event(member2, test_song2)
        print("Done logging play event.")
        print(f"Logging like event for song: {test_song1}")
        await profiler.log_user_like_song(member1, test_song2)
        await profiler.log_user_like_song(member2, test_song1)
        await profiler.log_user_like_song(member3, test_song2)
        await profiler.log_user_skip_song(member1, test_song3)
        print("Done logging like event.")


    asyncio.run(main())
