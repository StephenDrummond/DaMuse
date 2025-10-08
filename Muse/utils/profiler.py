import math
from datetime import datetime

import discord

from db.db import Database


class Profiler(object):
    def __init__(self):
        self.db = Database()

        async def log_user_play_event(self, member: discord.Member, song: str) -> None:
            # Record that a user has played a song (e.g., for analytics or preference tracking)
            # Query db if user has already played this song,
            # If user has not already played this song, store in user_like_song with todays date and default
            # preference score of 0.5 (0.5 is the default value for this on the db)
            pass

        async def log_user_like_song(self, member: discord.Member, song: str) -> None:
            # Record that a user liked a song (e.g., to update preference profile or recommendations)
            # Boost the users preference_score for this song
            pass

        async def log_user_dislike_song(self, member: discord.Member, song: str) -> None:
            # Record that a user disliked a song (e.g., to avoid similar songs in recommendations)
            # Either set the preference score of the user to 0 or maybe make a new table holding dislikes,
            # not sure about the approach here
            pass

        async def log_user_skip_song(self, member: discord.Member, song: str) -> None:
            # Record that a user skipped a song (e.g., to adjust song recommendations or user profile)
            # Decrease boost preference by -0.2, skipping is nuanced but usually means that the user does
            # not like the song.
            pass

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
