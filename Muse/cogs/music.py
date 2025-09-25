import asyncio
import os
import discord
from discord.ext import commands
from utils.youtube import YTDLSource
from music_state.queues import queues

FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn'
}

FFMPEG_PATH = os.path.join(os.getcwd(), "ffmpeg", "bin", "ffmpeg.exe")


class Music(commands.Cog):
    def __init__(self, bot):
        self.stop_music = False
        self.bot = bot

    @commands.command()
    async def play(self, ctx, *, search: str = None):
        if not ctx.author.voice:
            await ctx.send("You must be in a voice channel to play music!")
            return

        if not search:
            await ctx.send("Please provide a song name or link.")
            return

        try:
            info = await YTDLSource.from_url(search, stream=True)
        except Exception as e:
            await ctx.send(f"Error retrieving track: {e}")
            return

        # Connect bot to user's voice channel if not already connected
        if not ctx.voice_client:
            await ctx.author.voice.channel.connect()
        elif ctx.voice_client.channel != ctx.author.voice.channel:
            await ctx.voice_client.move_to(ctx.author.voice.channel)

        if not info:
            await ctx.send("Couldn't find anything.")
            return

        queues[ctx.guild.id].append(info)

        if ctx.voice_client and not ctx.voice_client.is_playing():
            await self._play_next_song(ctx)
        else:
            await ctx.send(f"Queueing: **{info['title']}**")

    @commands.command()
    async def skip(self, ctx):
        if ctx.voice_client.is_playing():
            ctx.voice_client.stop()

    @commands.command()
    async def stop(self, ctx):
        if ctx.voice_client.is_playing():
            self.stop_music = True
            ctx.voice_client.stop()

    async def _play_next_song(self, ctx):
        if self.stop_music:
            self.stop_music = False
            return

        if not queues[ctx.guild.id]:
            await ctx.send("No more songs queued.")
            return

        info = queues[ctx.guild.id].popleft()  # Get the next song
        source = discord.FFmpegPCMAudio(
            info["url"],
            executable=FFMPEG_PATH,
            **FFMPEG_OPTIONS
        )

        def after_playing(error):
            if error:
                print(f"Player error: {error}")
            coro = self._play_next_song(ctx)  # Play next song
            fut = asyncio.run_coroutine_threadsafe(coro, self.bot.loop)
            try:
                fut.result()
            except Exception as e:
                print(f"Error playing next song: {e}")

        ctx.voice_client.play(source, after=after_playing)
        await ctx.send(f"Now playing: **{info['title']}**")


async def setup(bot):
    await bot.add_cog(Music(bot))