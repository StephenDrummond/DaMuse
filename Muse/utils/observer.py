import asyncio
from typing import Dict

import redis

from db.db import Database
from music_state.channel_members import channels_and_members
from utils.curator import Curator
from utils.db_client import DBClient


class Observer(DBClient):
    curator_list: Dict[int, Curator] = {}
    r = redis.from_url("redis://localhost")

    def __init__(self, db):
        super().__init__(db)
        for guild_id, channel_ids in channels_and_members.items():
            for channel_id, member_list in channel_ids.items():
                self.curator_list[channel_id] = Curator(db, channel_id, member_list)

    async def load_user_prefs_into_memory(self, channel_id, discord_id):
        query = await self.preference_query_builder("song_user_likes")
        rows = await self.db.fetch(
            query, discord_id
        )  # rows is a list of asyncpg.Record
        key = f"{channel_id}:{discord_id}:genre"

        print(query)
        print(rows)

    async def remove_user_prefs_from_memory(self, channel_id, user_id): ...

    @staticmethod
    async def preference_query_builder(pref_table: str) -> str:
        """
        takes in a preference table and returns a query that gets all the given users preferences in descending order
        :param pref_table:
        :return:
        """
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
    o = Observer(db)
    await o.load_user_prefs_into_memory(69420, 123456)
    await o.load_user_prefs_into_memory(69420, 123456)
    await o.load_user_prefs_into_memory(69420, 234567)
    await o.load_user_prefs_into_memory(69420, 234567)


if __name__ == "__main__":
    asyncio.run(main())
