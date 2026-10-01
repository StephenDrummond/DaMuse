import asyncio
import logging
import sys

from app import DaMuseBot, Services
from config import Settings


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    logging.getLogger("discord.player").setLevel(logging.WARNING)

    settings = Settings.from_env()
    if not settings.discord_token:
        sys.exit("DISCORD_TOKEN environment variable not set")

    services = await Services.create(settings)
    try:
        async with DaMuseBot(services) as bot:
            await bot.start(settings.discord_token)
    finally:
        await services.close()


if __name__ == "__main__":
    asyncio.run(main())
