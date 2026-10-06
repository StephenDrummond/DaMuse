import logging
from typing import Dict, Optional

import discord
from discord.ext import commands

from app import DaMuseBot
from music_state import inactivity
from music_state.controller import PlaybackController
from utils.audio_resolver import Playable

logger = logging.getLogger(__name__)

# Both sources are read over HTTP, so let ffmpeg ride out dropped connections
RECONNECT_OPTIONS = "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5"


async def audio_source(playable: Playable, ffmpeg_path: str) -> discord.FFmpegOpusAudio:
    if playable.from_cache:
        # Already Ogg Opus at 48 kHz: codec="opus" makes ffmpeg pass the
        # packets through untouched, so cached songs cost almost no CPU
        return discord.FFmpegOpusAudio(
            playable.url,
            codec="opus",
            executable=ffmpeg_path,
            before_options=RECONNECT_OPTIONS,
            options="-vn",
        )
    # Straight from YouTube: probe, then copy if Opus or encode if not.
    # discord.py's "native" probe only swaps in ffprobe when the executable is
    # literally "ffmpeg"; given a path (FFMPEG_PATH) it would run ffmpeg with
    # ffprobe's options, fail, and log an error before falling back. So go
    # straight to the fallback probe, which uses ffmpeg itself.
    return await discord.FFmpegOpusAudio.from_probe(
        playable.url,
        method="native" if ffmpeg_path == "ffmpeg" else "fallback",
        executable=ffmpeg_path,
        before_options=RECONNECT_OPTIONS,
        options="-vn",
    )


class Music(commands.Cog):
    """Discord commands for playback; the logic lives in PlaybackController."""

    def __init__(self, bot: DaMuseBot) -> None:
        self.bot = bot
        self.services = bot.services
        self.controllers: Dict[int, PlaybackController] = {}  # guild id -> state

    def _voice(self, guild_id: int) -> Optional[discord.VoiceClient]:
        guild = self.bot.get_guild(guild_id)
        if guild is None or not isinstance(guild.voice_client, discord.VoiceClient):
            return None
        return guild.voice_client

    def _controller(self, guild: discord.Guild) -> PlaybackController:
        controller = self.controllers.get(guild.id)
        if controller is None:
            services = self.services
            ffmpeg_path = services.settings.ffmpeg_path
            controller = PlaybackController(
                guild.id,
                voice=lambda: self._voice(guild.id),
                resolver=services.resolver,
                curator=services.curator,
                profiler=services.profiler,
                make_source=lambda playable: audio_source(playable, ffmpeg_path),
                on_idle=lambda channel: inactivity.start_timer(guild, channel),
                on_active=lambda: inactivity.cancel_timer(guild.id),
            )
            self.controllers[guild.id] = controller
        return controller

    @commands.command()
    async def play(
        self, ctx: commands.Context, *, search: Optional[str] = None
    ) -> None:
        """Play a song by search term, YouTube URL or Spotify track link."""
        voice_state = getattr(ctx.author, "voice", None)
        if ctx.guild is None or voice_state is None or voice_state.channel is None:
            await ctx.send("You must be in a voice channel to play music!")
            return

        if not search:
            await ctx.send("Please provide a song name or link.")
            return

        # Join or move to the user's voice channel
        channel = voice_state.channel
        voice_client = self._voice(ctx.guild.id)
        if voice_client is None:
            await channel.connect()
        elif voice_client.channel != channel:
            await voice_client.move_to(channel)

        controller = self._controller(ctx.guild)
        controller.text_channel = ctx.channel

        try:
            track = await self.services.resolver.resolve(
                search, requested_by=ctx.author.id
            )
        except Exception:
            logger.exception("Error retrieving track for %r", search)
            await ctx.send("Couldn't retrieve that track.")
            return
        if track is None:
            await ctx.send("Couldn't find anything.")
            return

        if await controller.enqueue(track):
            await ctx.send(f"Queued **{track.title}**")

    @commands.command()
    async def skip(self, ctx: commands.Context) -> None:
        """Skip the current song (counts against it for whoever skipped)."""
        controller = self.controllers.get(ctx.guild.id) if ctx.guild else None
        if controller is None or not controller.skip(ctx.author.id):
            await ctx.send("Nothing is playing.")

    @commands.command()
    async def stop(self, ctx: commands.Context) -> None:
        """Stop playback and clear the queue."""
        controller = self.controllers.get(ctx.guild.id) if ctx.guild else None
        if controller is None:
            return
        controller.stop()
        await ctx.send("Stopped and cleared the queue.")

    @commands.command()
    async def like(self, ctx: commands.Context) -> None:
        """Tell DaMuse you like the current song."""
        await self._rate(ctx, "like")

    @commands.command()
    async def dislike(self, ctx: commands.Context) -> None:
        """Tell DaMuse you don't like the current song."""
        await self._rate(ctx, "dislike")

    async def _rate(self, ctx: commands.Context, event_type: str) -> None:
        controller = self.controllers.get(ctx.guild.id) if ctx.guild else None
        result = (
            await controller.rate(ctx.author.id, event_type)
            if controller is not None
            else "nothing_playing"
        )
        if result == "nothing_playing":
            await ctx.send("Nothing is playing.")
        elif result == "unidentified":
            await ctx.send(
                "Couldn't identify this song on Spotify, so it can't be rated."
            )
        else:
            await ctx.message.add_reaction("👍" if event_type == "like" else "👎")

    @commands.Cog.listener()
    async def on_voice_state_update(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ) -> None:
        """Drop a guild's playback state when the bot leaves its voice channel."""
        if self.bot.user and member.id == self.bot.user.id and after.channel is None:
            self.controllers.pop(member.guild.id, None)
            inactivity.cancel_timer(member.guild.id)


async def setup(bot: DaMuseBot) -> None:
    await bot.add_cog(Music(bot))
