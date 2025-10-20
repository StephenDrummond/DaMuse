import asyncio
import os
from typing import Optional, Dict, Any

import discord  # type: ignore
from discord.ext import commands  # type: ignore

from api.youtube import YTDLSource
from music_state.queues import queues

# Options for FFmpeg to handle streaming
FFMPEG_OPTIONS: Dict[str, str] = {
    "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
    "options": "-vn -f opus -ac 2 -ar 48000",  # No video
}

# Path to ffmpeg executable
FFMPEG_PATH: str = os.path.join(os.getcwd(), "ffmpeg", "bin", "ffmpeg.exe")


class Music(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        """
        Initializes the Music cog.

        :param bot: The Discord bot instance.
        """
        self.stop_music: bool = False  # Flag to stop playback
        self.bot: commands.Bot = bot
        self.db = bot.db  # type: ignore
        # librarian: Librarian = Librarian(self.db)  # Librarian instance (unused here)

    @commands.command()
    async def play(
        self, ctx: commands.Context, *, search: Optional[str] = None
    ) -> None:
        """
        Play a song by URL or search term.

        :param ctx: Context of the command.
        :param search: Song URL or search term.
        """
        # Ensure the user is in a voice channel
        if not ctx.author.voice:  # type: ignore
            await ctx.send("You must be in a voice channel to play music!")
            return

        # Ensure a search term or URL was provided
        if not search:
            await ctx.send("Please provide a song name or link.")
            return

        try:
            # Add song to queue
            await YTDLSource.from_url(search, ctx)
        except Exception as e:
            print(f"Error retrieving track: {e}")
            return

        # Join or move to the user's voice channel
        if not ctx.voice_client:
            await ctx.author.voice.channel.connect()  # type: ignore
        elif ctx.voice_client.channel != ctx.author.voice.channel:  # type: ignore
            await ctx.voice_client.move_to(ctx.author.voice.channel)  # type: ignore

        # Play the next song if not already playing
        if ctx.voice_client and not ctx.voice_client.is_playing():  # type: ignore
            await self._play_next_song(ctx)

    @commands.command()
    async def skip(self, ctx: commands.Context) -> None:
        """
        Skip the currently playing song.

        :param ctx: Context of the command.
        """
        if ctx.voice_client and ctx.voice_client.is_playing():  # type: ignore
            ctx.voice_client.stop()  # type: ignore

    @commands.command()
    async def stop(self, ctx: commands.Context) -> None:
        """
        Stop playback and clear the queue.

        :param ctx: Context of the command.
        """
        if ctx.voice_client and ctx.voice_client.is_playing():  # type: ignore
            self.stop_music = True
            ctx.voice_client.stop()  # type: ignore

    async def _play_next_song(self, ctx: commands.Context) -> None:
        """
        Internal method to play the next song in the queue.

        :param ctx: Context of the command.
        """
        if self.stop_music:
            # Stop flag was set, reset it and stop playback
            self.stop_music = False
            return

        if not queues.get(ctx.guild.id):  # type: ignore # No songs queued
            await ctx.send("No more songs queued.")
            return

        # Get the next song in the queue
        info: Dict[str, Any] = queues[ctx.guild.id].popleft()  # type: ignore

        # Create audio source for FFmpeg
        source: discord.FFmpegOpusAudio = await discord.FFmpegOpusAudio.from_probe(
            info["url"], **FFMPEG_OPTIONS
        )

        def after_playing(error: Optional[Exception]) -> None:
            """
            Callback after song finishes.

            :param error: Error encountered during playback, if any.
            """
            if error:
                print(f"Player error: {error}")

            coro = self._play_next_song(ctx)  # Play next song
            fut = asyncio.run_coroutine_threadsafe(coro, self.bot.loop)
            try:
                fut.result()
            except Exception as e:
                print(f"Error playing next song: {e}")

        # Start playing the song
        ctx.voice_client.play(source, after=after_playing)  # type: ignore
        await ctx.send(f"Now playing: **{info['title']}**")


async def setup(bot: commands.Bot) -> None:
    """
    Load the Music cog.

    :param bot: The Discord bot instance.
    """
    await bot.add_cog(Music(bot))
