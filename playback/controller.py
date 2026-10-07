import asyncio
import functools
import logging
from collections import deque
from typing import (
    Any,
    Awaitable,
    Callable,
    Deque,
    Literal,
    Optional,
    Protocol,
    Set,
)

from discord.abc import Messageable

from audio.audio_resolver import AudioResolver, Playable, Track
from taste.curator import Curator, Pick
from taste.profiler import PlayRecord, Profiler

logger = logging.getLogger(__name__)

MAX_START_ATTEMPTS = 3  # tracks to try before giving up when streams fail

RateResult = Literal["ok", "nothing_playing", "unidentified"]
Prepared = tuple[Track, Pick]  # a Curator pick, already resolved to a track


class VoiceConnection(Protocol):
    """The slice of discord.VoiceClient the controller uses (so tests can
    substitute a fake)."""

    @property
    def channel(self) -> Any: ...

    def is_playing(self) -> bool: ...

    def play(
        self, source: Any, *, after: Callable[[Optional[Exception]], Any]
    ) -> Any: ...

    def stop(self) -> None: ...


def listener_ids(channel: Any) -> list[int]:
    """Discord ids of the humans in a voice channel."""
    return [member.id for member in getattr(channel, "members", []) if not member.bot]


class PlaybackController:
    """Playback state machine for one guild: the queue, what's playing, and
    what happens when a song ends, is skipped or stopped.

    A guild has at most one voice connection, living in whichever process owns
    the guild's shard, so this state is deliberately in-process.

    Discord specifics are injected, which is what makes this testable:
    `voice` returns the guild's current connection (or None), `make_source`
    turns a Playable into an audio source, and `on_idle` / `on_active` start
    and cancel the inactivity timer.
    """

    def __init__(
        self,
        guild_id: int,
        *,
        voice: Callable[[], Optional[VoiceConnection]],
        resolver: AudioResolver,
        curator: Curator,
        profiler: Profiler,
        make_source: Callable[[Playable], Awaitable[Any]],
        on_idle: Callable[[Messageable], None],
        on_active: Callable[[], None],
    ) -> None:
        self.guild_id = guild_id
        self._voice = voice
        self.resolver = resolver
        self.curator = curator
        self.profiler = profiler
        self._make_source = make_source
        self._on_idle = on_idle
        self._on_active = on_active

        self.queue: Deque[Track] = deque()
        self.current: Optional[Track] = None
        # resolves to the `plays` row for `current` (None if it couldn't be
        # identified); a task so playback never waits on Spotify / Postgres
        self.current_play: Optional["asyncio.Task[Optional[PlayRecord]]"] = None
        self.skipped = False  # current song ended via !skip
        self.stopping = False  # !stop: don't advance when the current song ends
        self.text_channel: Optional[Messageable] = None  # for announcements
        # the room's next pick, prepared while the current song plays so the
        # next one starts without a gap (see _prepare_upcoming)
        self._upcoming: Optional["asyncio.Task[Optional[Prepared]]"] = None

        # serializes "start the next song" so concurrent !play / track-end
        # callbacks can't both start playback
        self._lock = asyncio.Lock()
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._background: Set["asyncio.Task[Any]"] = set()

    # --- commands --------------------------------------------------------

    async def enqueue(self, track: Track) -> bool:
        """Add a track; start it if nothing's playing. Returns True if it's
        waiting in the queue (rather than playing, or failed to start)."""
        self.stopping = False
        self.queue.append(track)
        if self.current is None:
            await self.play_next()
        # checked afterwards, not before: a concurrent enqueue may have
        # started another song while this one waited for the lock
        return any(queued is track for queued in self.queue)

    async def curate(self) -> bool:
        """Start playing (a queued request, else a pick for the room) if
        nothing is playing. False if something already is: the Curator takes
        over by itself when the queue runs out."""
        self.stopping = False
        if self.current is not None:
            return False
        await self.play_next()
        return True

    def skip(self, user_id: int) -> bool:
        """Skip the current song (counts against it for `user_id`). False if
        nothing is playing or a skip is already underway."""
        voice = self._voice()
        if voice is None or self.current is None or self.skipped:
            return False
        self.skipped = True
        if self.current_play is not None:
            self._spawn(self._log(self.current_play, [user_id], "skip"))
        self._end_current(voice)
        return True

    def stop(self) -> None:
        """Clear the queue and stop the current song without advancing."""
        self.queue.clear()
        self._discard_upcoming()
        voice = self._voice()
        if voice is not None and self.current is not None:
            self.stopping = True
            self._end_current(voice)

    async def rate(self, user_id: int, event_type: str) -> RateResult:
        """Record a like/dislike from `user_id` for the current song."""
        play_task = self.current_play
        if play_task is None:
            return "nothing_playing"
        try:
            play = await play_task
        except Exception:
            logger.exception("Recording the current play failed")
            return "unidentified"
        if play is None:
            return "unidentified"
        await self.profiler.log_event(play, [user_id], event_type)
        return "ok"

    # --- playback --------------------------------------------------------

    async def play_next(self) -> None:
        """Start the next song (queued request, else a Curator pick), unless one
        is already playing."""
        self._loop = asyncio.get_running_loop()
        async with self._lock:
            for _ in range(MAX_START_ATTEMPTS):
                voice = self._voice()
                if voice is None or self.current is not None:
                    return

                try:
                    track, pick = await self._next_track(voice.channel)
                    if track is None:
                        await self.announce(
                            "Nothing left to play, and not enough listening history "
                            "in this room to pick something. `!play` a song!"
                        )
                        if self.text_channel is not None:
                            self._on_idle(self.text_channel)
                        return
                    source = await self._make_source(
                        await self.resolver.playable(track)
                    )
                except Exception:
                    logger.exception(
                        "Couldn't start the next track in %s", self.guild_id
                    )
                    await self.announce("Couldn't play that one, skipping.")
                    continue

                self.current = track
                self.skipped = False
                self.current_play = self._spawn(
                    self.profiler.record_play(
                        self.guild_id,
                        voice.channel.id,
                        track.hint_title,
                        track.hint_artist,
                        track.requested_by,
                        song_id=pick.song_id if pick else None,
                    )
                )
                self._on_active()
                # bind the track, so a late callback can't end a later song
                voice.play(source, after=functools.partial(self._after_play, track))

                self._prepare_upcoming(voice.channel)

                suffix = " (picked for the room)" if pick else ""
                await self.announce(f"Now playing: **{track.title}**{suffix}")
                return

    async def _next_track(self, channel: Any) -> tuple[Optional[Track], Optional[Pick]]:
        """Next requested song, else the pick prepared during the last song,
        else a fresh pick for the room."""
        if self.queue:
            return self.queue.popleft(), None

        upcoming, self._upcoming = self._upcoming, None
        if upcoming is not None:
            prepared = await upcoming  # usually done already: no wait
            if prepared is not None:
                return prepared
        # nothing was prepared, or it fell through: pick now
        picked = await self._pick_for_room(channel)
        return picked if picked is not None else (None, None)

    def _prepare_upcoming(self, channel: Any) -> None:
        """Start picking the song after this one in the background, unless
        requests are queued (they play first) or a pick is already prepared
        (it waits behind requests and stays valid)."""
        if self.queue or self._upcoming is not None:
            return
        self._upcoming = self._spawn(self._pick_for_room(channel, self.current_play))

    def _discard_upcoming(self) -> None:
        if self._upcoming is not None:
            self._upcoming.cancel()
            self._upcoming = None

    async def _pick_for_room(
        self,
        channel: Any,
        playing: Optional["asyncio.Task[Optional[PlayRecord]]"] = None,
    ) -> Optional[Prepared]:
        """Ask the Curator for the room's next song and resolve it to a track.
        `playing` is the song still playing, excluded explicitly because its
        `plays` row (which the recent-plays check uses) may not exist yet.
        Resolving here also queues an uncached pick for the S3 worker, so it
        may already be cached by the time it plays."""
        try:
            exclude: list[int] = []
            if playing is not None:
                try:
                    record = await playing
                except Exception:
                    record = None  # logged where the play is recorded
                if record is not None:
                    exclude.append(record.track.song_id)

            pick = await self.curator.pick_next(
                channel.id, listener_ids(channel), exclude_song_ids=exclude
            )
            if pick is None:
                return None
            track = await self.resolver.resolve(
                f"{pick.artist} - {pick.title}",
                requested_by=None,
                hint=(pick.title, pick.artist),
            )
            return (track, pick) if track is not None else None
        except Exception:
            logger.exception("Couldn't pick a song for the room in %s", self.guild_id)
            return None

    def _end_current(self, voice: VoiceConnection) -> None:
        if voice.is_playing():
            voice.stop()  # discord.py then calls _after_play
        elif self.current is not None:
            # marked as playing but the connection isn't (dropped audio, a
            # reconnect...): advance anyway rather than wedge the guild
            self._after_play(self.current, None)

    def _after_play(self, ended: Track, error: Optional[Exception]) -> None:
        """discord.py calls this from its audio thread when `ended` finishes."""
        if error:
            logger.error("Player error in guild %s: %s", self.guild_id, error)
        if self._loop is not None:
            self._loop.call_soon_threadsafe(self._track_ended, ended, error)

    def _track_ended(self, ended: Track, error: Optional[Exception]) -> None:
        self._spawn(self._on_track_end(ended, error))

    async def _on_track_end(self, ended: Track, error: Optional[Exception]) -> None:
        try:
            if self.current is not ended:
                # a late or duplicate callback for a song that's already been
                # handled; acting on it would end whatever is playing now
                return

            # everyone still in the room heard the song out, unless it was cut
            # short by !skip, !stop or an error
            finished = not self.skipped and not self.stopping and error is None
            voice = self._voice()
            listeners = (
                listener_ids(voice.channel) if finished and voice is not None else []
            )
            if self.current_play is not None:
                self._spawn(self._log(self.current_play, listeners, "listen"))
            self.current = None
            self.current_play = None

            if self.stopping:
                self.stopping = False
                if self.text_channel is not None:
                    self._on_idle(self.text_channel)
                return
            await self.play_next()
        except Exception:
            logger.exception("Error advancing playback in guild %s", self.guild_id)

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

    # --- helpers ---------------------------------------------------------

    async def announce(self, message: str) -> None:
        if self.text_channel is not None:
            await self.text_channel.send(message)

    def _spawn(self, coro: Awaitable[Any]) -> "asyncio.Task[Any]":
        task = asyncio.ensure_future(coro)
        self._background.add(task)
        task.add_done_callback(self._background.discard)
        return task

    async def settle(self) -> None:
        """Wait until all background work (track-end handling, event logging)
        has finished, including work it spawns. For tests and shutdown."""
        idle_rounds = 0
        while idle_rounds < 3:
            await asyncio.sleep(0)  # let call_soon_threadsafe callbacks run
            if self._background:
                idle_rounds = 0
                await asyncio.gather(*list(self._background), return_exceptions=True)
            else:
                idle_rounds += 1
