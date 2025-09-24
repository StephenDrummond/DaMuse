import os

import discord
from discord.ext import commands
from utils.youtube import YTDLSource

FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn'
}

FFMPEG_PATH = os.path.join(os.getcwd(), "ffmpeg", "bin", "ffmpeg.exe")


class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def play(self, ctx, *, search: str = None):
        if not ctx.author.voice:
            await ctx.send("You must be in a voice channel to play music!")
            return

        if not search:
            await ctx.send("Please provide a song name or link.")
            return

        # Connect bot to user's voice channel if not already connected
        if not ctx.voice_client:
            await ctx.author.voice.channel.connect()
        elif ctx.voice_client.channel != ctx.author.voice.channel:
            await ctx.voice_client.move_to(ctx.author.voice.channel)

        # Connect if not already in VC
        if not ctx.voice_client:
            await ctx.author.voice.channel.connect()

        try:
            info = await YTDLSource.from_url(search, loop=self.bot.loop, stream=True)
        except Exception as e:
            await ctx.send(f"Error retrieving track: {e}")
            return

        if not info:
            await ctx.send("Couldn't find anything.")
            return

        ffmpeg_options = {"options": "-vn"}
        source = discord.FFmpegPCMAudio(
            info["url"],
            executable=FFMPEG_PATH,
            **ffmpeg_options
        )

        ctx.voice_client.stop()
        ctx.voice_client.play(
            source,
            after=lambda e: print(f"Player error: {e}") if e else None
        )

        await ctx.send(f"Now playing: **{info['title']}**")


async def setup(bot):
    await bot.add_cog(Music(bot))