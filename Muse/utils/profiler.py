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

    async def log_user_play_event(self, member: discord.Member, song: str, alpha: float = 0.2) -> None:
        """
        Log that a user has played a song and update their preference profile.

        This method performs the following:
        1. Retrieves metadata for the given song from Spotify.
        2. Looks up the song and artist IDs in the database.
        3. Inserts or updates preference records for both the song and artist.

        Args:
            member (discord.Member): The Discord user who played the song.
            song (str): The name of the song played.
            alpha (float) : The increment by which preference score is updated by
        Returns:
            None
        """
        member_id: int = member.id

        # Fetch song metadata from Spotify
        info: dict[str, Any] = await get_spotify_info(song)
        song_name: str = info["name"]
        artist_name: str = info["artists"][0]
        genres: list[str] = info.get("genres", [])

        # Fetch IDs for the song and artist from the database
        song_id: int = await self.db.fetch_val("SELECT id FROM songs WHERE title = $1", song_name)
        artist_id: int = await self.db.fetch_val("SELECT id FROM artists WHERE name = $1", artist_name)

        # Insert or update song preference record
        await self.upsert_like(
            table_name="song_user_likes",
            user_id=member_id,
            target_id=song_id,
            liked_at=datetime.today(),
            target_column="song_id",
            alpha=alpha
        )

        # Insert or update artist preference record
        await self.upsert_like(
            table_name="artist_user_likes",
            user_id=member_id,
            target_id=artist_id,
            liked_at=datetime.today(),
            target_column="artist_id",
            alpha=alpha
        )

        for genre in genres:
            genre_id: int = await self.db.fetch_val("SELECT id FROM genres WHERE name = $1", genre)
            await self.upsert_like(
                table_name="genre_user_likes",
                user_id=member_id,
                target_id=genre_id,
                liked_at=datetime.today(),
                target_column="genre_id",
                alpha=alpha
            )

    async def log_user_like_song(self, member: discord.Member, song: str, alpha=0.4) -> None:
        # Record that a user liked a song (e.g., to update preference profile or recommendations)
        # Boost the users preference_score for this song
        member_id = member.id

        info = await get_spotify_info(song)

    async def log_user_dislike_song(self, member: discord.Member, song: str) -> None:
        # Record that a user disliked a song (e.g., to avoid similar songs in recommendations)
        # Either set the preference score of the user to 0 or maybe make a new table holding dislikes,
        # not sure about the approach here
        ...

    async def log_user_skip_song(self, member: discord.Member, song: str) -> None:
        # Record that a user skipped a song (e.g., to adjust song recommendations or user profile)
        # Decrease boost preference by -0.2, skipping is nuanced but usually means that the user does
        # not like the song.
        ...

    async def log_user_listened_to(self, member: discord.Member, song: str) -> None:
        ...

    async def upsert_like(
            self,
            table_name: str,
            user_id: int,
            target_id: int,
            liked_at: datetime,
            target_column: str,
            alpha: float,
    ) -> None:
        """
        Inserts a like record into a table, or updates it on conflict.

        Args:
            table_name: Name of the table (e.g., "song_user_likes").
            user_id: ID of the user.
            target_id: ID of the song or artist.
            liked_at: Timestamp of the like.
            target_column: The column name for the target ID (e.g., "song_id", "artist_id").
        """
        query = f"""
            INSERT INTO {table_name} (user_id, {target_column}, liked_at)
            VALUES ($1, $2, $3)
            ON CONFLICT (user_id, {target_column}) DO UPDATE
            SET preference_score = LEAST({table_name}.preference_score + {alpha}, 1.0),
                liked = true,
                liked_at = $3;
        """
        await self.db.execute(query, user_id, target_id, liked_at)


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

        # Test song name
        test_song1 = "Money Pink Floyd"
        test_song2 = "Rockafeller skank"

        print(f"Logging play event for song: {test_song1}")
        await profiler.log_user_play_event(member1, test_song1)
        await profiler.log_user_play_event(member2, test_song2)
        print("Done logging play event.")


    asyncio.run(main())
