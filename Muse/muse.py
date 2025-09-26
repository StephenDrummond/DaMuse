import logging
import discord
import os
import asyncio
from dotenv import load_dotenv
from discord.ext import commands

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

logging.basicConfig(level=logging.INFO)
logging.getLogger("discord.player").setLevel(logging.WARNING)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")


async def main():
    async with bot:
        await bot.load_extension("cogs.general")
        await bot.load_extension("cogs.music")
        await bot.start(TOKEN)


asyncio.run(main())