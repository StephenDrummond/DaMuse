import asyncio
import json
from typing import Dict

import redis
from redis import Redis

from utils.curator import Curator
from utils.db_client import DBClient


class Observer(DBClient):
    """Observer is a singleton class which inherits the DBClient class meant to observe
    all the channel states and makes updates to the Redis cache when a
    user joins or leaves a channel. Manages creation and deletion of the Curator
    class"""

    curators: Dict[int, Curator] = {}  # maps channel_id -> Curator instance
    r: Redis  # Redis client

    _instance = None
    _initialized = False

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, db):
        # prevent reinitialization
        if not self._initialized:
            super().__init__(db)
            self.r = redis.from_url("redis://localhost")
            self._initialized = True

    async def update_cache(self, channel_id, discord_id, keystr: str):
        data = self.read_cache(channel_id, discord_id, keystr)

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
        channel_id:discord_id:keystr  :  """
        # fetch user preference rows from database
        rows = await self.fetch_preferences(discord_id, table)
        if rows is None:
            return

        key = self.key_creator(channel_id, discord_id, table.split('_', 1)[0])

        data = [[row[0], round(row[1], 4)] for row in rows]

        data_json = json.dumps(  # turns data into a string, needs to be json.load()ed to read values
            data
        )

        await self.r.set(key, data_json)

    async def read_cache(self, channel_id, discord_id, keystr: str):
        key = self.key_creator(channel_id, discord_id, keystr)
        data = await self.r.get(key)

        return json.loads(data)

    async def delete_cache(self, channel_id, discord_id):
        # remove user data from Redis
        await asyncio.gather(
            self.r.delete(self.key_creator(channel_id, discord_id, 'song')),
            self.r.delete(self.key_creator(channel_id, discord_id, 'artist')),
            self.r.delete(self.key_creator(channel_id, discord_id, 'genre')),
        )

        # update in-memory member tracking
        self.curators[channel_id].member_ids.remove(discord_id)

        # delete Curator if channel becomes empty
        if len(self.curators[channel_id].member_ids) == 0:
            del self.curators[channel_id]

    @staticmethod
    def key_creator(channel_id: int, discord_id: int, keystr: str):
        """ Creates a redis key string,
        example -> 'channel_id:discord_id:song' """
        return f"{channel_id}:{discord_id}:{keystr}"
