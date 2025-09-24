import discord
import os
from dotenv import load_dotenv
from discord.ext import commands
from utils.helpers import is_valid_url

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')

@bot.command()
async def hello(ctx):
    await ctx.send(f'Hello {ctx.author}!')

@bot.command()
async def play(ctx, song_link: str = None):
    if song_link is None:
        await ctx.send("Please provide a link to play!")
        return
    elif (is_valid_url(song_link)):
        await ctx.send(f'Now playing {song_link}!')
    else:
        await ctx.send(f'Invalid link!')

bot.run(TOKEN)