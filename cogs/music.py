import asyncio
import logging
import os
from typing import Awaitable, Dict, Optional, Set

import discord
from discord.ext import commands

from api.audio_store import AudioStore
from music_state import inactivity
from music_state.player import GuildPlayer
from utils.audio_jobs import AudioJobs
from utils.audio_resolver import AudioResolver, Playable, Track
from utils.curator import Curator, Pick
from utils.profiler import PlayRecord, Profiler

logger = logging.getLogger(__name__)

# Both sources are read over HTTP, so let ffmpeg ride out dropped connections
RECONNECT_OPTIONS = "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5"

# ffmpeg executable; defaults to the one on PATH. On Windows, point it at the
# vendored build with FFMPEG_PATH=ffmpeg/bin/ffmpeg.exe in .env.
FFMPEG_PATH: str = os.getenv("FFMPEG_PATH", "ffmpeg")

MAX_START_ATTEMPTS = 3  # tracks to try before giving up when streams fail


def listener_ids(channel: discord.abc.Connectable) -> list[int]:
    """Discord ids of the humans in a voice channel."""
    members = getattr(channel, "members", [])
    return [member.id for member in members if not member.bot]


class Music(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        """
        Initializes the Music cog.

        :param bot: The Discord bot instance.
        """
        self.bot: commands.Bot = bot
        self.db = bot.db  # type: ignore
        self.profiler = Profiler(self.db)
        self.curator = Curator(self.db)
        self.resolver = AudioResolver(AudioStore.from_env(), AudioJobs(self.db))
        self.players: Dict[int, GuildPlayer] = {}  # guild id -> playback state
        self._background: Set[asyncio.Task] = set()  # keeps tasks from being GC'd

    def _player(self, guild_id: int) -> GuildPlayer:
        return self.players.setdefault(guild_id, GuildPlayer())

    @staticmethod
    def _voice(guild: Optional[discord.Guild]) -> Optional[discord.VoiceClient]:
        if guild is None or not isinstance(guild.voice_client, discord.VoiceClient):
            return None
        return guild.voice_client

    def _spawn(self, coro: Awaitable[None]) -> None:
        task = asyncio.ensure_future(coro)
        self._background.add(task)
        task.add_done_callback(self._background.discard)

    @commands.command()
    async def play(
        self, ctx: commands.Context, *, search: Optional[str] = None
    ) -> None:
        """
        Play a song by URL or search term.

        :param ctx: Context of the command.
        :param search: Song URL or search term.
        """
        voice_state = getattr(ctx.author, "voice", None)
        if ctx.guild is None or voice_state is None or voice_state.channel is None:
            await ctx.send("You must be in a voice channel to play music!")
            return

        if not search:
            await ctx.send("Please provide a song name or link.")
            return

        # Join or move to the user's voice channel
        channel = voice_state.channel
        voice_client = self._voice(ctx.guild)
        if voice_client is None:
            await channel.connect()
        elif voice_client.channel != channel:
            await voice_client.move_to(channel)

        player = self._player(ctx.guild.id)
        player.text_channel = ctx.channel
        player.stopping = False

        try:
            track = await self.resolver.resolve(search, requested_by=ctx.author.id)
        except Exception:
            logger.exception("Error retrieving track for %r", search)
            await ctx.send("Couldn't retrieve that track.")
            return
        if track is None:
            await ctx.send("Couldn't find anything.")
            return

        player.queue.append(track)
        if player.current is not None:
            await ctx.send(f"Queued **{track.title}**")
        else:
            await self._play_next(ctx.guild)

    @commands.command()
    async def skip(self, ctx: commands.Context) -> None:
        """
        Skip the currently playing song (counts against it for whoever skipped).

        :param ctx: Context of the command.
        """
        voice_client = self._voice(ctx.guild)
        player = self.players.get(ctx.guild.id) if ctx.guild else None
        if voice_client is None or player is None or player.current is None:
            await ctx.send("Nothing is playing.")
            return

        player.skipped = True
        if player.current_play is not None:
            self._spawn(self._log(player.current_play, [ctx.author.id], "skip"))
        voice_client.stop()  # triggers _on_track_end, which plays the next song

    @commands.command()
    async def stop(self, ctx: commands.Context) -> None:
        """
        Stop playback and clear the queue.

        :param ctx: Context of the command.
        """
        voice_client = self._voice(ctx.guild)
        player = self.players.get(ctx.guild.id) if ctx.guild else None
        if player is None:
            return

        player.queue.clear()
        if voice_client is not None and player.current is not None:
            player.stopping = True
            voice_client.stop()
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
        player = self.players.get(ctx.guild.id) if ctx.guild else None
        if player is None or player.current_play is None:
            await ctx.send("Nothing is playing.")
            return

        play = await player.current_play
        if play is None:
            await ctx.send(
                "Couldn't identify this song on Spotify, so it can't be rated."
            )
            return
        await self.profiler.log_event(play, [ctx.author.id], event_type)
        await ctx.message.add_reaction("👍" if event_type == "like" else "👎")

    async def _next_track(
        self, player: GuildPlayer, channel: discord.abc.Connectable
    ) -> tuple[Optional[Track], Optional[Pick]]:
        """Next requested song, or else the Curator's pick for the room."""
        if player.queue:
            return player.queue.popleft(), None

        channel_id = getattr(channel, "id")
        pick = await self.curator.pick_next(channel_id, listener_ids(channel))
        if pick is None:
            return None, None
        track = await self.resolver.resolve(
            f"{pick.artist} - {pick.title}",
            requested_by=None,
            hint=(pick.title, pick.artist),
        )
        return track, pick if track else None

    @staticmethod
    async def _audio_source(playable: Playable) -> discord.FFmpegOpusAudio:
        if playable.from_cache:
            # Already Ogg Opus at 48 kHz: codec="opus" makes ffmpeg pass the
            # packets through untouched, so cached songs cost almost no CPU
            return discord.FFmpegOpusAudio(
                playable.url,
                codec="opus",
                executable=FFMPEG_PATH,
                before_options=RECONNECT_OPTIONS,
                options="-vn",
            )
        # Straight from YouTube: probe, then copy if Opus or encode if not
        return await discord.FFmpegOpusAudio.from_probe(
            playable.url,
            executable=FFMPEG_PATH,
            before_options=RECONNECT_OPTIONS,
            options="-vn",
        )

    async def _play_next(self, guild: discord.Guild) -> None:
        """Start the next song in the guild, unless one is already playing."""
        player = self._player(guild.id)
        async with player.lock:
            for _ in range(MAX_START_ATTEMPTS):
                voice_client = self._voice(guild)
                if voice_client is None or player.current is not None:
                    return

                try:
                    track, pick = await self._next_track(player, voice_client.channel)
                    if track is None:
                        await self._announce(
                            player,
                            "Queue's empty, and there isn't enough listening history "
                            "to pick for this room yet. `!play` something!",
                        )
                        if player.text_channel is not None:
                            inactivity.start_timer(guild, player.text_channel)
                        return

                    playable = await self.resolver.playable(track)
                    source = await self._audio_source(playable)
                except Exception:
                    logger.exception("Couldn't start the next track in %s", guild.id)
                    await self._announce(player, "Couldn't play that one, skipping.")
                    continue

                player.current = track
                player.skipped = False
                player.current_play = asyncio.create_task(
                    self.profiler.record_play(
                        guild.id,
                        voice_client.channel.id,
                        track.hint_title,
                        track.hint_artist,
                        track.requested_by,
                        song_id=pick.song_id if pick else None,
                    )
                )
                inactivity.cancel_timer(guild.id)
                voice_client.play(
                    source, after=lambda error: self._after_play(guild, error)
                )

                if pick is None:
                    await self._announce(player, f"Now playing: **{track.title}**")
                else:
                    await self._announce(
                        player, f"Now playing: **{track.title}** (picked for the room)"
                    )
                return

    def _after_play(self, guild: discord.Guild, error: Optional[Exception]) -> None:
        """discord.py calls this from its audio thread when a track ends."""
        if error:
            logger.error("Player error in guild %s: %s", guild.id, error)
        # hand off to the event loop without blocking the audio thread
        asyncio.run_coroutine_threadsafe(
            self._on_track_end(guild, error), self.bot.loop
        )

    async def _on_track_end(
        self, guild: discord.Guild, error: Optional[Exception]
    ) -> None:
        try:
            player = self._player(guild.id)
            voice_client = self._voice(guild)

            # everyone still in the room heard the song out
            finished = not player.skipped and error is None
            listeners = (
                listener_ids(voice_client.channel)
                if finished and voice_client is not None
                else []
            )
            if player.current_play is not None:
                self._spawn(self._log(player.current_play, listeners, "listen"))
            player.current = None
            player.current_play = None

            if player.stopping:
                player.stopping = False
                if player.text_channel is not None:
                    inactivity.start_timer(guild, player.text_channel)
                return
            await self._play_next(guild)
        except Exception:
            logger.exception("Error advancing playback in guild %s", guild.id)

    async def _log(
        self,
        play_task: "asyncio.Task[Optional[PlayRecord]]",
        user_ids: list[int],
        event_type: str,
    ) -> None:
        """Log an event once the play is recorded. Always awaits the task so a
        failed record_play is logged rather than silently dropped."""
        try:
            play = await play_task
            if play is not None and user_ids:
                await self.profiler.log_event(play, user_ids, event_type)
        except Exception:
            logger.exception("Couldn't log %s event", event_type)

    @staticmethod
    async def _announce(player: GuildPlayer, message: str) -> None:
        if player.text_channel is not None:
            await player.text_channel.send(message)

    @commands.Cog.listener()
    async def on_voice_state_update(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ) -> None:
        """Drop a guild's playback state when the bot leaves its voice channel."""
        if self.bot.user and member.id == self.bot.user.id and after.channel is None:
            self.players.pop(member.guild.id, None)
            inactivity.cancel_timer(member.guild.id)


async def setup(bot: commands.Bot) -> None:
    """
    Load the Music cog.

    :param bot: The Discord bot instance.
    """
    await bot.add_cog(Music(bot))
