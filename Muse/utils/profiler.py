import math
from datetime import datetime
from typing import Any

import discord

from db.db import Database
from utils.spotify import get_spotify_info


class Profiler(object):
    def __init__(self):
        self.db = Database()

    async def log_user_play_event(
            self,
            member: discord.Member,
            song: str,
            start_preference_score: float = 0.5
    ) -> None:
        """
        Log that a user has played a song and update their preference profile.

        This method performs the following:
        1. Retrieves metadata for the given song from Spotify.
        2. Looks up the song and artist IDs in the database.
        3. Inserts or updates preference records for both the song and artist.

        Args:
            member (discord.Member): The Discord user who played the song.
            song (str): The name of the song played.
            start_preference_score (float, optional): Initial preference score if none exists.
                Defaults to 0.5.

        Returns:
            None
        """
        # Extract user ID
        member_id: int = member.id

        # Fetch song metadata from Spotify
        info: dict[str, Any] = await get_spotify_info(song)  # assuming get_spotify_info is async
        song_name: str = info["name"]
        artist_name: str = info["artists"][0]
        genres: list[str] = info.get("genres", [])

        # Fetch database IDs for the song and artist
        song_id: int = await self.db.fetch_val("SELECT id FROM songs WHERE title = $1", song_name)
        artist_id: int = await self.db.fetch_val("SELECT id FROM artists WHERE name = $1", artist_name)

        # Insert or update song preference record
        await self.upsert_like(
            table_name="song_user_likes",
            user_id=member_id,
            target_id=song_id,
            liked_at=datetime.today(),
            target_column="song_id"
        )

        # Insert or update artist preference record
        await self.upsert_like(
            table_name="artist_user_likes",
            user_id=member_id,
            target_id=artist_id,
            liked_at=datetime.today(),
            target_column="artist_id"
        )

        for genre in genres:
            genre_id: int = await self.db.fetch_val("SELECT id FROM genres WHERE name = $1", genre)
            await self.upsert_like(
                table_name="genre_user_likes",
                user_id=member_id,
                target_id=genre_id,
                liked_at=datetime.today(),
                target_column="genre_id"
            )

    async def log_user_like_song(self, member: discord.Member, song: str) -> None:
        # Record that a user liked a song (e.g., to update preference profile or recommendations)
        # Boost the users preference_score for this song
        ...

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

    @staticmethod
    def boost_preference(preference_score, alpha=0.2):
        preference_score += alpha

        date = datetime.today().date()

        return {
            preference_score: preference_score,
            date: date
        }

    @staticmethod
    def forget_preference(preference_score, last_updated, _lambda=0.05):
        delta = (datetime.today().date() - last_updated).days
        return preference_score * math.exp(-delta * _lambda)

    async def upsert_like(
            self,
            table_name: str,
            user_id: int,
            target_id: int,
            liked_at: datetime,
            target_column: str
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
            SET preference_score = {table_name}.preference_score + 0.2,
                liked = true,
                liked_at = $3;
        """
        await self.db.execute(query, user_id, target_id, liked_at)
