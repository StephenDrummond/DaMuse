import asyncio
import os
import discord
from discord.ext import commands
from utils.youtube import YTDLSource
from music_state.queues import queues
from collections import deque

FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn'
}

FFMPEG_PATH = os.path.join(os.getcwd(), "ffmpeg", "bin", "ffmpeg.exe")


class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.stop_music = False

    @commands.command()
    async def play(self, ctx, *, search: str = None):
        """Play a song or add it to the queue."""
        if not ctx.author.voice:
            return await ctx.send("You must be in a voice channel to play music!")

        if not search:
            return await ctx.send("Please provide a song name or link.")

        try:
            info = await asyncio.to_thread(YTDLSource.from_url_sync, search, True)
        except Exception as e:
            return await ctx.send(f"Error retrieving track: {e}")

        if not info:
            return await ctx.send("Couldn't find anything.")

        guild_id = ctx.guild.id
        if guild_id not in queues:
            queues[guild_id] = deque()

        queues[guild_id].append(info)
        await ctx.send(f"Queued: **{info['title']}**")

        # Connect bot if not already in VC or if moved
        await self.ensure_voice(ctx)

        # If nothing is playing, start playback
        if not ctx.voice_client.is_playing():
            asyncio.create_task(self._play_next_song(ctx))

    async def ensure_voice(self, ctx):
        """Ensure bot is in the correct voice channel."""
        if not ctx.voice_client:
            await ctx.author.voice.channel.connect()
        elif ctx.voice_client.channel != ctx.author.voice.channel:
            await ctx.voice_client.move_to(ctx.author.voice.channel)

    @commands.command()
    async def skip(self, ctx):
        """Skip current song."""
        if ctx.voice_client and ctx.voice_client.is_playing():
            ctx.voice_client.stop()
            await ctx.send("Skipped current song.")
        else:
            await ctx.send("Nothing is playing to skip.")

    @commands.command()
    async def stop(self, ctx):
        """Stop playing and clear queue."""
        if ctx.voice_client and ctx.voice_client.is_playing():
            self.stop_music = True
            queues[ctx.guild.id].clear()
            ctx.voice_client.stop()
            await ctx.send("Stopped playback and cleared queue.")
        else:
            await ctx.send("Nothing is playing.")

    async def _play_next_song(self, ctx):
        """Play next song in the queue."""
        guild_id = ctx.guild.id

        if self.stop_music or not queues.get(guild_id):
            self.stop_music = False
            await ctx.send("No more songs in the queue.")
            return

        info = queues[guild_id].popleft()
        source = await discord.FFmpegOpusAudio.from_probe(
            info["url"],
            executable=FFMPEG_PATH,
            **FFMPEG_OPTIONS
        )

        def after_playing(error):
            if error:
                print(f"[ERROR] Player error: {error}")
            # Schedule the next song
            fut = asyncio.run_coroutine_threadsafe(self._play_next_song(ctx), self.bot.loop)
            try:
                fut.result()
            except Exception as e:
                print(f"[ERROR] Failed to play next song: {e}")

        ctx.voice_client.play(source, after=after_playing)
        await ctx.send(f"Now playing: **{info['title']}**")


async def setup(bot):
    await bot.add_cog(Music(bot))
