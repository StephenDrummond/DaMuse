import time
from dataclasses import replace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from api.audio_store import CachedAudio
from api.youtube import STREAM_TTL_SECONDS, VideoInfo, VideoRef
from utils.audio_resolver import AudioResolver, Playable, Track

REF = VideoRef(audio_key="youtube/abc", url="https://www.youtube.com/watch?v=abc")
CACHED = CachedAudio(
    key="audio/youtube/abc.opus",
    title="Pink Floyd - Money",
    hint_title="Money",
    hint_artist="Pink Floyd",
    source_url=REF.url,
    duration=382.0,
)
INFO = VideoInfo(
    audio_key="youtube/abc",
    url=REF.url,
    title="Pink Floyd - Money",
    stream_url="https://stream",
    hint_title="Money",
    hint_artist="Pink Floyd",
    duration=382.0,
    resolved_at=time.monotonic(),
)


@pytest.fixture
def store():
    store = MagicMock()
    store.lookup = AsyncMock(return_value=None)
    store.playback_url.return_value = "https://signed"
    return store


@pytest.fixture
def jobs():
    return AsyncMock()


@pytest.fixture
def youtube():
    with patch("utils.audio_resolver.youtube") as youtube:
        youtube.find = AsyncMock(return_value=REF)
        youtube.extract = AsyncMock(return_value=INFO)
        youtube.is_url = MagicMock(return_value=False)
        yield youtube


@pytest.mark.asyncio
async def test_cache_hit_skips_extraction_and_queue(store, jobs, youtube):
    store.lookup.return_value = CACHED

    track = await AudioResolver(store, jobs).resolve("money", requested_by=1)

    assert track is not None
    assert track.cached_key == CACHED.key
    assert (track.title, track.hint_artist, track.requested_by) == (
        CACHED.title,
        "Pink Floyd",
        1,
    )
    youtube.extract.assert_not_awaited()
    jobs.enqueue.assert_not_awaited()


@pytest.mark.asyncio
async def test_cache_miss_streams_and_queues_job(store, jobs, youtube):
    track = await AudioResolver(store, jobs).resolve("money", requested_by=1)

    assert track is not None
    assert track.cached_key is None
    assert track.stream == INFO
    youtube.extract.assert_awaited_once_with(REF.url)
    jobs.enqueue.assert_awaited_once_with("youtube/abc", REF.url)


@pytest.mark.asyncio
async def test_queue_failure_does_not_block_playback(store, jobs, youtube):
    jobs.enqueue.side_effect = RuntimeError("db down")

    assert await AudioResolver(store, jobs).resolve("money", requested_by=1)


@pytest.mark.asyncio
async def test_no_store_streams_without_queueing(jobs, youtube):
    track = await AudioResolver(None, jobs).resolve("money", requested_by=1)

    assert track is not None and track.stream == INFO
    jobs.enqueue.assert_not_awaited()


@pytest.mark.asyncio
async def test_search_without_results(store, jobs, youtube):
    youtube.find.return_value = None

    assert await AudioResolver(store, jobs).resolve("zzz", requested_by=1) is None
    youtube.extract.assert_not_awaited()


@pytest.mark.asyncio
async def test_other_site_url_checks_cache_after_extraction(store, jobs, youtube):
    youtube.find.return_value = None
    youtube.is_url.return_value = True
    store.lookup.return_value = CACHED

    track = await AudioResolver(store, jobs).resolve("https://x.com/a", requested_by=1)

    youtube.extract.assert_awaited_once_with("https://x.com/a")
    assert track is not None and track.cached_key == CACHED.key


@pytest.mark.asyncio
async def test_spotify_link_searches_youtube_with_exact_hint(store, jobs, youtube):
    with (
        patch("utils.audio_resolver.spotify_track_id", return_value="sp1"),
        patch(
            "utils.audio_resolver.get_track_title_artist",
            new_callable=AsyncMock,
            return_value=("Money", "Pink Floyd"),
        ),
    ):
        track = await AudioResolver(store, jobs).resolve(
            "https://open.spotify.com/track/sp1", requested_by=1
        )

    youtube.find.assert_awaited_once_with("Pink Floyd - Money")
    assert track is not None
    assert (track.hint_title, track.hint_artist) == ("Money", "Pink Floyd")


@pytest.mark.asyncio
async def test_explicit_hint_overrides_metadata(store, jobs, youtube):
    store.lookup.return_value = CACHED

    track = await AudioResolver(store, jobs).resolve(
        "q", requested_by=None, hint=("Title", "Artist")
    )

    assert track is not None
    assert (track.hint_title, track.hint_artist) == ("Title", "Artist")


def stream_track(**changes):
    track = Track(
        audio_key="youtube/abc",
        title="t",
        source_url=REF.url,
        requested_by=1,
        hint_title="t",
        hint_artist=None,
        stream=INFO,
    )
    return replace(track, **changes)


@pytest.mark.asyncio
async def test_playable_cached_track(store, jobs):
    track = stream_track(cached_key=CACHED.key, stream=None)

    playable = await AudioResolver(store, jobs).playable(track)

    assert playable == Playable("https://signed", from_cache=True)
    store.lookup.assert_not_awaited()


@pytest.mark.asyncio
async def test_playable_picks_up_newly_cached_file(store, jobs):
    store.lookup.return_value = CACHED

    playable = await AudioResolver(store, jobs).playable(stream_track())

    assert playable.from_cache
    store.playback_url.assert_called_once_with(CACHED.key)


@pytest.mark.asyncio
async def test_playable_fresh_stream(store, jobs, youtube):
    playable = await AudioResolver(store, jobs).playable(stream_track())

    assert playable == Playable("https://stream", from_cache=False)
    youtube.extract.assert_not_awaited()


@pytest.mark.asyncio
async def test_playable_re_resolves_stale_stream(store, jobs, youtube):
    stale = replace(INFO, resolved_at=time.monotonic() - STREAM_TTL_SECONDS - 1)
    youtube.extract.return_value = replace(INFO, stream_url="https://fresh")

    playable = await AudioResolver(store, jobs).playable(stream_track(stream=stale))

    assert playable.url == "https://fresh"
    youtube.extract.assert_awaited_once_with(REF.url)


@pytest.mark.asyncio
async def test_playable_raises_when_source_gone(store, jobs, youtube):
    youtube.extract.return_value = None

    with pytest.raises(LookupError):
        await AudioResolver(store, jobs).playable(stream_track(stream=None))
