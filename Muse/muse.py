import asyncio
import logging
import os

import asyncpg
import discord
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASS")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

logging.basicConfig(level=logging.INFO)
logging.getLogger("discord.player").setLevel(logging.WARNING)


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")


async def init_db_pool():
    try:
        bot.pool = await asyncpg.create_pool(
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT,
            min_size=5,  # min number of connections
            max_size=20,  # max number of connections
        )
        print("Database pool created")
    except Exception as e:
        print(e)


async def main():
    async with bot:
        await init_db_pool()
        await bot.load_extension("cogs.general")
        await bot.load_extension("cogs.music")
        await bot.load_extension("cogs.channel_events")
        await bot.start(TOKEN)


asyncio.run(main())
