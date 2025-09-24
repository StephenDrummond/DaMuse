from discord.ext import commands

from music_state.inactivity import start_timer
from utils.helpers import is_valid_url
from music_state.queues import queues
import asyncio

class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def play(self, ctx, song_link: str = None):
        # Check: user must be in a voice channel
        if not ctx.author.voice:
            await ctx.send("You must be in a voice channel to play music!")
            return

        # Check: link must be provided and valid
        if not song_link or not is_valid_url(song_link):
            await ctx.send("Please provide a valid link to play!")
            return

        channel = ctx.author.voice.channel

        # Connect if not already connected
        if not ctx.voice_client:
            await channel.connect()
            await ctx.send(f"Joined {channel.name}!")

        # Add song to queue
        queues.setdefault(ctx.guild.id, []).append(song_link)
        print (queues)
        await ctx.send(f"Added to queue: {song_link}")

        # Restart inactivity timer
        start_timer(ctx.guild, ctx.channel, delay=20)

async def setup(bot):
    await bot.add_cog(Music(bot))