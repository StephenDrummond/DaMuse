import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from music_state.controller import MAX_START_ATTEMPTS, PlaybackController
from utils.audio_resolver import Playable, Track
from utils.curator import Pick
from utils.librarian import TrackIds
from utils.profiler import PlayRecord

CHANNEL_ID = 10
ALICE, BOB, BOT = 1, 2, 99


def member(member_id, bot=False):
    return SimpleNamespace(id=member_id, bot=bot)


class FakeVoice:
    """Mimics discord.VoiceClient: play() refuses while already playing, and
    stop() / finish() invoke the `after` callback like the audio thread does."""

    def __init__(self, members):
        self.channel = SimpleNamespace(id=CHANNEL_ID, members=members)
        self.source = None
        self.after = None
        self.plays = []

    def is_playing(self):
        return self.source is not None

    def play(self, source, *, after):
        if self.source is not None:
            raise RuntimeError("Already playing audio.")
        self.source, self.after = source, after
        self.plays.append(source)

    def _end(self, error):
        after, self.source, self.after = self.after, None, None
        assert after is not None
        after(error)

    def stop(self):
        if self.source is not None:
            self._end(None)

    def finish(self, error=None):
        """The song reaches its end (or the player errors)."""
        self._end(error)


def track(name, requested_by=ALICE):
    return Track(
        audio_key=f"youtube/{name}",
        title=name,
        source_url=f"https://youtu.be/{name}",
        requested_by=requested_by,
        hint_title=name,
        hint_artist="artist",
    )


def play_record(play_id=1):
    return PlayRecord(play_id=play_id, track=TrackIds(1, 2, [3]))


@pytest.fixture
def voice():
    return FakeVoice([member(ALICE), member(BOB), member(BOT, bot=True)])


@pytest.fixture
def resolver():
    resolver = MagicMock()
    resolver.playable = AsyncMock(
        side_effect=lambda t: Playable(f"https://cdn/{t.title}", from_cache=True)
    )
    resolver.resolve = AsyncMock()
    return resolver


@pytest.fixture
def curator():
    curator = MagicMock()
    curator.pick_next = AsyncMock(return_value=None)
    return curator


@pytest.fixture
def profiler():
    profiler = MagicMock()
    profiler.record_play = AsyncMock(return_value=play_record())
    profiler.log_event = AsyncMock()
    return profiler


@pytest.fixture
def text_channel():
    channel = MagicMock()
    channel.send = AsyncMock()
    return channel


@pytest.fixture
def hooks():
    return SimpleNamespace(idle=MagicMock(), active=MagicMock())


@pytest.fixture
def controller(voice, resolver, curator, profiler, text_channel, hooks):
    controller = PlaybackController(
        123,
        voice=lambda: voice,
        resolver=resolver,
        curator=curator,
        profiler=profiler,
        # the "source" is just the URL, so tests can see what played
        make_source=AsyncMock(side_effect=lambda playable: playable.url),
        on_idle=hooks.idle,
        on_active=hooks.active,
    )
    controller.text_channel = text_channel
    return controller


def sent(text_channel):
    return [call.args[0] for call in text_channel.send.await_args_list]


def events(profiler):
    """(user ids, event type) for every log_event call."""
    return [(c.args[1], c.args[2]) for c in profiler.log_event.await_args_list]


@pytest.mark.asyncio
async def test_enqueue_when_idle_starts_playing(
    controller, voice, profiler, text_channel, hooks
):
    queued = await controller.enqueue(track("a"))
    await controller.settle()

    assert queued is False
    assert voice.plays == ["https://cdn/a"]
    assert controller.current is not None and controller.current.title == "a"
    profiler.record_play.assert_awaited_once_with(
        123, CHANNEL_ID, "a", "artist", ALICE, song_id=None
    )
    hooks.active.assert_called_once()
    assert sent(text_channel) == ["Now playing: **a**"]


@pytest.mark.asyncio
async def test_enqueue_while_playing_queues(controller, voice):
    await controller.enqueue(track("a"))
    queued = await controller.enqueue(track("b"))

    assert queued is True
    assert voice.plays == ["https://cdn/a"]
    assert [t.title for t in controller.queue] == ["b"]


@pytest.mark.asyncio
async def test_finished_song_logs_listen_for_humans_and_advances(
    controller, voice, profiler
):
    await controller.enqueue(track("a"))
    await controller.enqueue(track("b"))

    voice.finish()
    await controller.settle()

    assert voice.plays == ["https://cdn/a", "https://cdn/b"]
    assert events(profiler) == [([ALICE, BOB], "listen")]  # bot excluded


@pytest.mark.asyncio
async def test_skip_logs_skip_only_and_advances(controller, voice, profiler):
    await controller.enqueue(track("a"))
    await controller.enqueue(track("b"))

    assert controller.skip(BOB) is True
    await controller.settle()

    assert voice.plays[-1] == "https://cdn/b"
    assert events(profiler) == [([BOB], "skip")]  # no "listen" for a skipped song


@pytest.mark.asyncio
async def test_double_skip_counts_once(controller, voice, profiler):
    await controller.enqueue(track("a"))
    await controller.enqueue(track("b"))
    await controller.enqueue(track("c"))
    voice.stop = MagicMock()  # the track-end callback hasn't happened yet

    assert controller.skip(BOB) is True
    assert controller.skip(BOB) is False
    await controller.settle()

    assert events(profiler) == [([BOB], "skip")]
    voice.stop.assert_called_once()


@pytest.mark.asyncio
async def test_skip_when_nothing_playing(controller):
    assert controller.skip(ALICE) is False


@pytest.mark.asyncio
async def test_skip_recovers_when_voice_is_not_actually_playing(controller, voice):
    await controller.enqueue(track("a"))
    await controller.enqueue(track("b"))
    voice.source = None  # audio dropped without a callback

    assert controller.skip(ALICE) is True
    await controller.settle()

    assert controller.current is not None and controller.current.title == "b"


@pytest.mark.asyncio
async def test_stop_clears_queue_without_listen_or_advance(
    controller, voice, profiler, hooks, text_channel
):
    await controller.enqueue(track("a"))
    await controller.enqueue(track("b"))

    controller.stop()
    await controller.settle()

    assert voice.plays == ["https://cdn/a"]
    assert not controller.queue
    assert controller.current is None
    assert events(profiler) == []  # stopping isn't "heard it through"
    hooks.idle.assert_called_once_with(text_channel)


@pytest.mark.asyncio
async def test_play_after_stop_resumes(controller, voice):
    await controller.enqueue(track("a"))
    controller.stop()
    await controller.settle()

    await controller.enqueue(track("b"))
    await controller.settle()

    assert voice.plays == ["https://cdn/a", "https://cdn/b"]


@pytest.mark.asyncio
async def test_player_error_skips_listen_and_advances(controller, voice, profiler):
    await controller.enqueue(track("a"))
    await controller.enqueue(track("b"))

    voice.finish(error=RuntimeError("stream died"))
    await controller.settle()

    assert voice.plays[-1] == "https://cdn/b"
    assert events(profiler) == []


@pytest.mark.asyncio
async def test_empty_queue_uses_curator_pick(
    controller, voice, curator, resolver, profiler, text_channel
):
    curator.pick_next.return_value = Pick(
        song_id=7, title="Money", artist="Pink Floyd", score=0.8
    )
    resolver.resolve.return_value = track("Money", requested_by=None)

    await controller.play_next()
    await controller.settle()

    curator.pick_next.assert_awaited_once_with(CHANNEL_ID, [ALICE, BOB])
    resolver.resolve.assert_awaited_once_with(
        "Pink Floyd - Money", requested_by=None, hint=("Money", "Pink Floyd")
    )
    assert voice.plays == ["https://cdn/Money"]
    assert profiler.record_play.await_args.kwargs == {"song_id": 7}
    assert sent(text_channel) == ["Now playing: **Money** (picked for the room)"]


@pytest.mark.asyncio
async def test_nothing_to_pick_announces_and_goes_idle(
    controller, voice, text_channel, hooks
):
    await controller.play_next()

    assert voice.plays == []
    assert "Nothing left to play" in sent(text_channel)[0]
    hooks.idle.assert_called_once_with(text_channel)


@pytest.mark.asyncio
async def test_unplayable_track_is_skipped(controller, voice, resolver, text_channel):
    resolver.playable.side_effect = [
        LookupError("gone"),
        Playable("https://cdn/b", from_cache=True),
    ]
    await controller.enqueue(track("a"))
    await controller.enqueue(track("b"))  # not queued behind: "a" never started
    await controller.settle()

    assert voice.plays == ["https://cdn/b"]
    assert "Couldn't play that one, skipping." in sent(text_channel)


@pytest.mark.asyncio
async def test_gives_up_after_max_attempts(controller, voice, resolver):
    resolver.playable.side_effect = LookupError("gone")
    for name in "abcde":
        controller.queue.append(track(name))

    await controller.play_next()

    assert voice.plays == []
    assert resolver.playable.await_count == MAX_START_ATTEMPTS


@pytest.mark.asyncio
async def test_concurrent_enqueues_start_one_song(controller, voice):
    results = await asyncio.gather(
        controller.enqueue(track("a")), controller.enqueue(track("b"))
    )
    await controller.settle()

    assert len(voice.plays) == 1  # FakeVoice would raise on a second play()
    assert results == [False, True]  # the second requester is told it's queued
    assert len(controller.queue) == 1


@pytest.mark.asyncio
async def test_no_voice_connection_does_nothing(controller, voice, profiler):
    controller._voice = lambda: None

    await controller.enqueue(track("a"))

    profiler.record_play.assert_not_awaited()


@pytest.mark.asyncio
async def test_duplicate_track_end_callback_is_ignored(controller, voice):
    await controller.enqueue(track("a"))
    await controller.enqueue(track("b"))
    after = voice.after

    voice.finish()
    await controller.settle()
    after(None)  # stale callback for "a"
    await controller.settle()

    assert voice.plays == ["https://cdn/a", "https://cdn/b"]
    assert controller.current is not None and controller.current.title == "b"


@pytest.mark.asyncio
async def test_failed_play_record_does_not_break_playback(controller, voice, profiler):
    profiler.record_play.side_effect = RuntimeError("db down")
    await controller.enqueue(track("a"))
    await controller.enqueue(track("b"))

    voice.finish()
    await controller.settle()

    assert voice.plays[-1] == "https://cdn/b"
    profiler.log_event.assert_not_awaited()


@pytest.mark.asyncio
async def test_rate_logs_event(controller, profiler):
    await controller.enqueue(track("a"))

    assert await controller.rate(BOB, "like") == "ok"
    assert events(profiler) == [([BOB], "like")]


@pytest.mark.asyncio
async def test_rate_nothing_playing(controller):
    assert await controller.rate(BOB, "like") == "nothing_playing"


@pytest.mark.asyncio
async def test_rate_unidentified_song(controller, profiler):
    profiler.record_play.return_value = None
    await controller.enqueue(track("a"))

    assert await controller.rate(BOB, "dislike") == "unidentified"
    profiler.log_event.assert_not_awaited()


@pytest.mark.asyncio
async def test_rate_when_record_failed(controller, profiler):
    profiler.record_play.side_effect = RuntimeError("db down")
    await controller.enqueue(track("a"))

    assert await controller.rate(BOB, "like") == "unidentified"
