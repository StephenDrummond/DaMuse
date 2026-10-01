import asyncio
import logging
import os
import sys

import discord
from discord.ext import commands
from dotenv import load_dotenv

from db.db import Database

load_dotenv()

TOKEN: str | None = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

# AutoShardedBot runs one shard per ~1000 guilds inside this process (Discord
# requires sharding past 2500). To spread shards across processes later, pass
# shard_ids=[...] and shard_count=N per process; all per-guild state is keyed
# by guild, so it stays with whichever process owns that guild's shard.
bot = commands.AutoShardedBot(command_prefix="!", intents=intents)

logging.basicConfig(level=logging.INFO)
logging.getLogger("discord.player").setLevel(logging.WARNING)


@bot.event
async def on_ready():
    logging.info("Logged in as %s (%d shards)", bot.user, bot.shard_count or 1)


async def main():
    if TOKEN is None:
        print("DISCORD_TOKEN environment variable not set")
        sys.exit(1)

    db = Database()
    await db.init_pool()
    bot.db = db  # type: ignore

    try:
        async with bot:
            await bot.load_extension("cogs.general")
            await bot.load_extension("cogs.music")
            await bot.load_extension("cogs.channel_events")
            await bot.start(TOKEN)
    finally:
        await db.close()


if __name__ == "__main__":
    asyncio.run(main())
