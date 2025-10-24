import asyncio
from concurrent.futures import ProcessPoolExecutor
from typing import Dict, Any

import yt_dlp  # type: ignore
from discord.ext import commands

from music_state.queues import queues

# yt_dlp configuration for audio extraction
ytdl_format_options: Dict[str, Any] = {
    "format": "bestaudio/best",  # Best audio quality
    "noplaylist": True,  # Only single track
    "quiet": True,  # Suppress yt-dlp output
    "default_search": "ytsearch",  # Search if not a URL
    "extractor_args": {
        "youtube": {
            "player_client": ["default", "-tv_simply"],  # Optimize extraction
        },
    },
}

# Initialize yt-dlp with the above options
ytdl = yt_dlp.YoutubeDL(ytdl_format_options)

executor = ProcessPoolExecutor()


def run_ytdl(url: str):
    return ytdl.extract_info(url, download=False)


class YTDLSource:
    @staticmethod
    async def search_song(url: str, ctx: commands.Context, stream: bool = True) -> None:
        """
        Extract audio info from URL or search term,
        add it to the queue, and start playback if not playing.

        :param url: YouTube URL or search term.
        :param ctx: Discord.py context object.
        :param stream: Whether to stream the audio or download it.
        """
        # Extract information from the URL or search term
        loop = asyncio.get_running_loop()
        info = await loop.run_in_executor(executor, run_ytdl, url)

        # If multiple entries (e.g., a search), take the first one
        if "entries" in info:
            info = info["entries"][0]

        # Build info dictionary with necessary details
        info = {
            "title": info["title"],  # Song title
            "url": (
                info["url"] if stream else ytdl.prepare_filename(info)
            ),  # Stream URL or file path
        }

        # Handle case where no information could be extracted
        if not info:
            await ctx.send("Couldn't find anything.")
            return

        # Add the track info to the channel's queue
        if ctx.guild is None:
            await ctx.send("Something went wrong. Try again later.")
            return

        channel_id = ctx.voice_client.channel.id  # type: ignore
        queues[channel_id].append(info)

        # If something is already playing, notify the user it's queued
        if ctx.voice_client and ctx.voice_client.is_playing():  # type: ignore
            await ctx.send(f"Queued **{info['title']}**")
