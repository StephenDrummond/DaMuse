import asyncio
import json
from typing import Dict

import redis.asyncio as redis

from db.db import Database
from utils.curator import Curator
from utils.db_client import DBClient


class Observer(DBClient):
    """Observer is a singleton class which inherits the DBClient class meant to observe
    all the channel states and makes updates to the Redis cache when a
    user joins or leaves a channel. Manages creation and deletion of the Curator
    class"""

    curators: Dict[int, Curator] = {}  # maps channel_id -> Curator instance
    r: redis.Redis

    _instance = None
    _initialized = False

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, db: Database):
        # prevent reinitialization
        if not self._initialized:
            super().__init__(db)
            self.r = redis.from_url("redis://localhost")
            self._initialized = True

    async def update_cache(
            self, channel_id, discord_id, keystr: str, item_id: int, pref_score: int
    ):
        data = await self.read_cache(channel_id, discord_id, keystr)
        if not data:
            return False

        data[item_id] = pref_score
        key = self.key_creator(channel_id, discord_id, keystr)
        await self.r.set(key, json.dumps(data))
        return True

    async def create_cache(self, channel_id, discord_id):
        # load all preference categories concurrently
        await asyncio.gather(
            self.load_prefs_into_memory(channel_id, discord_id, "song_user_likes"),
            self.load_prefs_into_memory(channel_id, discord_id, "genre_user_likes"),
            self.load_prefs_into_memory(channel_id, discord_id, "artist_user_likes"),
        )

        # ensure Curator exists for channel and update member list
        if channel_id not in self.curators:
            self.curators[channel_id] = Curator(
                self.db, channel_id, [discord_id], self.r
            )
        else:
            self.curators[channel_id].member_ids.append(discord_id)

    async def load_prefs_into_memory(self, channel_id, discord_id, table: str):
        """Loads prefs into redis cache in this format
        channel_id:discord_id:keystr  :"""
        # fetch user preference rows from database
        rows = await self.fetch_preferences(discord_id, table)
        if rows is None:
            return

        key = self.key_creator(channel_id, discord_id, table.split("_", 1)[0])

        song_id_index = 0
        preference_score_index = 2
        data = {
            row[song_id_index]: round(row[preference_score_index], 4) for row in rows
        }

        data_json = json.dumps(  # turns data into a string, needs to be json.load()ed to read values
            data
        )

        await self.r.set(key, data_json)

    async def read_cache(
            self, channel_id, discord_id, keystr: str
    ) -> dict[int, float] | None:
        key = self.key_creator(channel_id, discord_id, keystr)
        data = await self.r.get(key)
        data = json.loads(data)

        return data

    async def delete_cache(self, channel_id, discord_id):
        # push updated value to Postgres

        await asyncio.gather(
            self.upsert_all_preferences(
                "song_user_likes", discord_id,
                await self.read_cache(channel_id, discord_id, "song"),
            ),
            self.upsert_all_preferences(
                "artist_user_likes", discord_id,
                await self.read_cache(
                    channel_id,
                    discord_id,
                    "artist",
                ),
            ),
            self.upsert_all_preferences(
                "genre_user_likes", discord_id,
                await self.read_cache(
                    channel_id,
                    discord_id,
                    "genre",
                ),
            ),
        )

        # remove user data from Redis
        await self.r.delete(
            self.key_creator(channel_id, discord_id, "song"),
            self.key_creator(channel_id, discord_id, "artist"),
            self.key_creator(channel_id, discord_id, "genre"),
        )

    async def delete_cache_update_curators(self, channel_id, discord_id):
        # upload memory to storage and delete.
        await self.delete_cache(channel_id, discord_id)
        # update curator holding that member
        self.curators[channel_id].member_ids.remove(discord_id)

        # delete Curator if channel becomes empty
        if len(self.curators[channel_id].member_ids) == 0:
            del self.curators[channel_id]

    @staticmethod
    def key_creator(channel_id: int, discord_id: int, keystr: str):
        """ Creates a redis key string,
        example -> 'channel_id:discord_id:song' """
        return f"{channel_id}:{discord_id}:{keystr}"


async def main():
    db = Database()
    await db.init_pool()
    o = Observer(db)
    cid = 1
    did = 283796442437517313
    key = o.key_creator(cid, did, "song")
    await o.create_cache(cid, did)
    print(await o.read_cache(cid, did, "song"))

    await o.update_cache(cid, did, "song", 1027, 1)
    print(type(await o.read_cache(cid, did, "song")))

    await o.delete_cache(cid, did)
    print(await o.r.get(key))


asyncio.run(main())
