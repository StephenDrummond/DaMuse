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

bot = commands.Bot(command_prefix="!", intents=intents)

logging.basicConfig(level=logging.INFO)
logging.getLogger("discord.player").setLevel(logging.WARNING)


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")


async def main():
    db = Database()
    await db.init_pool()
    bot.db = db  # type: ignore

    async with bot:
        if TOKEN is None:
            print("DISCORD_TOKEN environment variable not set")
            sys.exit(1)
        await bot.load_extension("cogs.general")
        await bot.load_extension("cogs.music")
        await bot.load_extension("cogs.channel_events")
        await bot.start(TOKEN)


if __name__ == "__main__":
    asyncio.run(main())
