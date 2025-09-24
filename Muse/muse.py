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

FFMPEG_PATH = os.path.join(os.getcwd(), "ffmpeg", "bin", "ffmpeg.exe")
print(FFMPEG_PATH)

bot = commands.Bot(command_prefix="!", intents=intents)

logging.basicConfig(level=logging.INFO)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")


async def main():
    async with bot:
        await bot.load_extension("cogs.general")
        await bot.load_extension("cogs.music")
        await bot.start(TOKEN)


asyncio.run(main())