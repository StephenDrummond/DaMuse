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

    curators: Dict[int, Curator] = {}
    r: Redis = None

    _instance = None  # class-level attribute

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, db):
        super().__init__(db)
        self.r = redis.from_url("redis://localhost")

    async def async_init(self):
        for guild_id, channel_ids in channels_and_members.items():
            for (
                    channel_id,
                    member_list,
            ) in channel_ids.items():  # all the members from every channel
                self.curators[channel_id] = (
                    Curator(  # one curator created for all active channels
                        self.db, channel_id, member_list
                    )
                )
                for member in member_list:
                    await self.cache_prefs(
                        channel_id, member
                    )  # can maybe speed this up with asyncio task gather

        print("Observer init done")

    async def cache_prefs(self, channel_id, discord_id):
        await asyncio.gather(  # concurrently load everything in to Redis
            self.load_prefs_into_memory(channel_id, discord_id, "song_user_likes"),
            self.load_prefs_into_memory(channel_id, discord_id, "genre_user_likes"),
            self.load_prefs_into_memory(channel_id, discord_id, "artist_user_likes"),
        )
        if (
                channel_id not in self.curators
        ):  # create a new Curator and add it to the curator_list with key = channel_id
            self.curators[channel_id] = Curator(self.db, channel_id, [discord_id])
        else:
            self.curators[channel_id].member_list.append(discord_id)

    async def load_prefs_into_memory(self, channel_id, discord_id, table: str):
        query = await self.pref_table_query_builder(table)

        rows = await self.db.fetch(
            query, discord_id
        )  # rows is a list of asyncpg.Record
        rows_as_lists = [list(row.values()) for row in rows]

        key = f"{channel_id}:{discord_id}:{table.split('_', 1)[0]}"
        for row in rows_as_lists:
            await self.r.rpush(key, *row)

    async def remove_user_prefs_from_cache(self, channel_id, user_id):
        await asyncio.gather(
            self.r.delete(f"{channel_id}:{user_id}:song"),
            self.r.delete(f"{channel_id}:{user_id}:artist"),
            self.r.delete(f"{channel_id}:{user_id}:genre"),
        )

        self.curators[channel_id].member_list.remove(user_id)

        if (
                len(self.curators[channel_id].member_list) == 0
        ):  # if member list is empty (no on in channel)
            del self.curators[channel_id]  # delete respective Curator

    @staticmethod
    async def pref_table_query_builder(pref_table: str) -> str:
        """
        takes in a preference table and returns a query that gets all the given users preferences in descending order
        :param pref_table:
        :return:
        """
        type_table = pref_table.split("_", 1)[0] + "s"  # ex: song_user_likes -> songs
        type_word = pref_table.split("_", 1)[0]  # ex: song_user_likes -> song

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
    o = Observer(db)
    await o.async_init()
    await o.cache_prefs(69420, 123456)
    await o.cache_prefs(69420, 123456)
    await o.cache_prefs(69420, 234567)
    await o.cache_prefs(69420, 234567)


if __name__ == "__main__":
    asyncio.run(main())
