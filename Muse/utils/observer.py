import asyncio
from typing import Dict

import redis
from redis import Redis

from db.db import Database
from music_state.channel_members import channels_and_members
from utils.curator import Curator
from utils.db_client import DBClient


class Observer(DBClient):
    """ Observer is a singleton class which inherits the DBClient class meant to observe
        the channels_and_members dictionary and makes updates to the Redis cache when a
        user joins or leaves a channel. Manages creation and deletion of the Curator
        class """

    curators: Dict[int, Curator] = {}  # maps channel_id -> Curator instance
    r: Redis = None  # Redis client

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

    async def async_init(self):
        # create Curator instances for all active channels
        tasks = []
        for guild_id, channel_ids in channels_and_members.items():
            for channel_id, member_list in channel_ids.items():
                self.curators[channel_id] = Curator(self.db, channel_id, member_list)
                for member in member_list:
                    tasks.append(self.cache_prefs(channel_id, member))
        await asyncio.gather(*tasks)
        print("Observer init done")

    async def cache_prefs(self, channel_id, discord_id):
        # load all preference categories concurrently
        await asyncio.gather(
            self.load_prefs_into_memory(channel_id, discord_id, "song_user_likes"),
            self.load_prefs_into_memory(channel_id, discord_id, "genre_user_likes"),
            self.load_prefs_into_memory(channel_id, discord_id, "artist_user_likes"),
        )

        # ensure Curator exists for channel and update member list
        if channel_id not in self.curators:
            self.curators[channel_id] = Curator(self.db, channel_id, [discord_id])
        else:
            self.curators[channel_id].member_list.append(discord_id)

    async def load_prefs_into_memory(self, channel_id, discord_id, table: str):
        query = self.pref_table_query_builder(table)
        # fetch user preference rows from database
        rows = await self.db.fetch(query, discord_id)
        rows_as_lists = [list(row.values()) for row in rows]

        key = f"{channel_id}:{discord_id}:{table.split('_', 1)[0]}"

        # Create async pipeline
        async with self.r.pipeline(transaction=False) as pipe:
            for row in rows_as_lists:
                # Queue commands — do NOT await these
                pipe.rpush(key, *row)
            # Execute the entire batch once
            await pipe.execute()

    async def remove_user_prefs_from_cache(self, channel_id, user_id):
        # remove user data from Redis
        await asyncio.gather(
            self.r.delete(f"{channel_id}:{user_id}:song"),
            self.r.delete(f"{channel_id}:{user_id}:artist"),
            self.r.delete(f"{channel_id}:{user_id}:genre"),
        )

        # update in-memory member tracking
        self.curators[channel_id].member_list.remove(user_id)

        # delete Curator if channel becomes empty
        if len(self.curators[channel_id].member_list) == 0:
            del self.curators[channel_id]

    @staticmethod
    def pref_table_query_builder(pref_table: str) -> str:
        """ Builds query for fetching a user’s preferences from given table name """
        type_table = pref_table.split("_", 1)[0] + "s"
        type_word = pref_table.split("_", 1)[0]

        query = f"""
                SELECT 
                tt.id AS {type_word}_id,
                tt.name AS {type_word}_name,
                pt.preference_score AS preference_score
                FROM users u
                JOIN {pref_table} pt ON u.id = pt.user_id
                JOIN {type_table} tt ON pt.{type_word}_id = tt.id
                WHERE u.discord_id = $1
                order by pt.preference_score DESC;"""
        return query


async def main():
    db = Database()
    await db.init_pool()
    o = Observer(db)  # singleton instance
    await o.async_init()
    await o.cache_prefs(69420, 123456)
    await o.cache_prefs(69420, 123456)
    await o.cache_prefs(69420, 234567)
    await o.cache_prefs(69420, 234567)


if __name__ == "__main__":
    asyncio.run(main())
