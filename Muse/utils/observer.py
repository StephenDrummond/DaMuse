from .db_client import DBClient


class Observer(DBClient):
    def __init__(self, db):
        super().__init__(db)


async def load_user_prefs_into_memory(self, user_id):
    ...


async def remove_user_prefs_from_memory(self, user_id):
    ...


import redis


def check_connection():
    try:
        # Connect to Redis (default port 6379)
        r = redis.Redis(host='localhost', port=6379, db=0)

        # Test connection
        r.ping()
        print("✅ Connected to Redis successfully!")

        # Test write
        r.set("test:key", "Hello, Redis!")
        value = r.get("test:key")

        # Decode and print
        print("Stored value:", value.decode())

        # Clean up
        r.delete("test:key")
        print("Test key removed.")

    except redis.ConnectionError:
        print("❌ Failed to connect to Redis. Is the server running?")


if __name__ == "__main__":
    test_redis()
