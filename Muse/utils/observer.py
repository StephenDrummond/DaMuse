import asyncio
import json
from typing import Dict

import redis
from redis import Redis

from utils.curator import Curator
from utils.db_client import DBClient


class Observer(DBClient):
    """Observer is a singleton class which inherits the DBClient class meant to observe
    the channels_and_members dictionary and makes updates to the Redis cache when a
    user joins or leaves a channel. Manages creation and deletion of the Curator
    class"""

    curators: Dict[int, Curator] = {}  # maps channel_id -> Curator instance
    r: Redis  # Redis client

    _instance = None
    _initialized = False

    def __new__(cls, *args, **kwargs):
        # enforce singleton behavior
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, db):
        # prevent reinitialization
        if not self._initialized:
            super().__init__(db)
            self.r = redis.from_url("redis://localhost")
            self._initialized = True

    async def cache_prefs(self, channel_id, discord_id):
        # load all preference categories concurrently
        await asyncio.gather(
            self.load_prefs_into_memory(channel_id, discord_id, "song_user_likes"),
            self.load_prefs_into_memory(channel_id, discord_id, "genre_user_likes"),
            self.load_prefs_into_memory(channel_id, discord_id, "artist_user_likes"),
        )

        # ensure Curator exists for channel and update member list
        if channel_id not in self.curators:
            self.curators[channel_id] = Curator(self.db, channel_id, [discord_id], self.r)
        else:
            self.curators[channel_id].member_ids.append(discord_id)

    async def load_prefs_into_memory(self, channel_id, discord_id, table: str):
        query = self.pref_table_query_builder(table)
        # fetch user preference rows from database
        rows = await self.db.fetch(query, discord_id)

        key = f"{channel_id}:{discord_id}:{table.split('_', 1)[0]}"

        data = [[row[0], round(row[1], 4)] for row in rows]

        data_json = json.dumps(
            data
        )  # turns data into a string, needs to be json.load()ed to read values

        await self.r.set(key, data_json)

    async def remove_user_prefs_from_cache(self, channel_id, user_id):
        # remove user data from Redis
        await asyncio.gather(
            self.r.delete(f"{channel_id}:{user_id}:song"),
            self.r.delete(f"{channel_id}:{user_id}:artist"),
            self.r.delete(f"{channel_id}:{user_id}:genre"),
        )

        # update in-memory member tracking
        self.curators[channel_id].member_ids.remove(user_id)

        # delete Curator if channel becomes empty
        if len(self.curators[channel_id].member_ids) == 0:
            del self.curators[channel_id]

    @staticmethod
    def pref_table_query_builder(pref_table: str) -> str:
        """Builds query for fetching a user’s preferences from given table name"""
        type_table = pref_table.split("_", 1)[0] + "s"
        type_word = pref_table.split("_", 1)[0]

        query = f"""
            (SELECT 
            tt.id AS {type_word}_id,
            tt.name AS {type_word}_name,
            pt.preference_score AS preference_score
            FROM users u
            JOIN {pref_table} pt ON u.id = pt.user_id
            JOIN {type_table} tt ON pt.{type_word}_id= tt.id
            WHERE u.discord_id = 123456
            and pt.preference_score > 0.7
            order by pt.preference_score desc
            limit 200
            )
            union all
            (SELECT 
            tt.id AS {type_word}_id,
            tt.name AS {type_word}_name,
            pt.preference_score AS preference_score
            FROM users u
            JOIN {pref_table} pt ON u.id = pt.user_id
            JOIN {type_table} tt ON pt.{type_word}_id = tt.id
            WHERE u.discord_id = 123456
            and pt.preference_score < 0.3
            order by pt.preference_score asc
            limit 200
            );"""
        return query
