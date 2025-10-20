import redis.asyncio as redis
import asyncio


async def test_redis():
    r = redis.from_url("redis://localhost")
    await r.set("ping", "pong")
    val = await r.get("ping")
    print(val)


asyncio.run(test_redis())
