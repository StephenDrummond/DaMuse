from typing import Dict

import redis

from music_state.channel_members import channels_and_members
from utils.curator import Curator
from .db_client import DBClient


class Observer(DBClient):
    curator_list: Dict[int, Curator] = {}

    def __init__(self, db):
        super().__init__(db)
        for guild_id, channel_ids in channels_and_members.items():
            for channel_id, member_list in channel_ids.items():
                self.curator_list[channel_id] = Curator(db, channel_id, member_list)


async def load_user_prefs_into_memory(self, channel_id, user_id): ...


async def remove_user_prefs_from_memory(self, channel_id, user_id): ...


def check_connection():
    try:
        # Connect to Redis (default port 6379)
        r = redis.Redis(host="localhost", port=6379, db=0)

        # Test connection
        r.ping()
        print("✅ Connected to Redis successfully!")

        # Test write
        r.set("test:key", "Hello, Redis!")
        value = r.get("test:key")

        # Decode and print
        # print("Stored value:", value.decode())

        # Clean up
        r.delete("test:key")
        print("Test key removed.")

    except redis.ConnectionError:
        print("❌ Failed to connect to Redis. Is the server running?")


if __name__ == "__main__":
    check_connection()
