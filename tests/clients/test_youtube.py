from concurrent.futures import ThreadPoolExecutor
from unittest.mock import MagicMock, patch

import pytest

from clients import youtube
from clients.youtube import (
    YouTubeClient,
    audio_key,
    is_url,
    parse_track_hint,
    youtube_video_id,
)


@pytest.mark.parametrize(
    "title, artist, channel, expected",
    [
        # yt-dlp music metadata wins
        ("Money", "Pink Floyd, Someone", None, ("Money", "Pink Floyd")),
        # "Artist - Title (noise)" format
        (
            "Pink Floyd - Money (Official Music Video)",
            None,
            None,
            ("Money", "Pink Floyd"),
        ),
        ("Drake - Passionfruit [Lyrics]", None, None, ("Passionfruit", "Drake")),
        # featuring credits stripped from both sides
        ("A ft. B - Song (Audio)", None, None, ("Song", "A")),
        ("A - Song feat. B", None, None, ("Song", "A")),
        # auto-generated topic channels name the artist
        ("Money", None, "Pink Floyd - Topic", ("Money", "Pink Floyd")),
        # nothing to go on
        ("some song", None, "random uploader", ("some song", None)),
        # non-noise brackets kept
        ("Song (Remix)", None, None, ("Song (Remix)", None)),
    ],
)
def test_parse_track_hint(title, artist, channel, expected):
    assert parse_track_hint(title, artist, channel) == expected


@pytest.mark.parametrize(
    "text, expected",
    [
        ("https://www.youtube.com/watch?v=dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ("https://youtube.com/watch?list=x&v=dQw4w9WgXcQ&t=3", "dQw4w9WgXcQ"),
        ("https://youtu.be/dQw4w9WgXcQ?si=abc", "dQw4w9WgXcQ"),
        ("https://www.youtube.com/shorts/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ("https://music.youtube.com/watch?v=dQw4w9WgXcQ", "dQw4w9WgXcQ"),
        ("never gonna give you up", None),
        ("https://soundcloud.com/a/b", None),
    ],
)
def test_youtube_video_id(text, expected):
    assert youtube_video_id(text) == expected


def test_audio_key_and_is_url():
    assert audio_key("Youtube", "abc") == "youtube/abc"
    assert is_url(" https://x.y/z")
    assert not is_url("artist - title")


@pytest.fixture
def client():
    """A YouTubeClient on a thread pool; tests patch the extraction functions."""
    client = YouTubeClient(ThreadPoolExecutor(max_workers=1))
    yield client
    client.close()


@pytest.mark.asyncio
async def test_find_youtube_url_needs_no_extraction():
    executor = MagicMock()
    ref = await YouTubeClient(executor).find("https://youtu.be/dQw4w9WgXcQ")

    executor.submit.assert_not_called()
    assert ref is not None
    assert ref.audio_key == "youtube/dQw4w9WgXcQ"
    assert ref.url == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"


@pytest.mark.asyncio
async def test_find_other_url_returns_none(client):
    assert await client.find("https://soundcloud.com/a/b") is None


@pytest.mark.asyncio
async def test_find_search_uses_flat_hit(client):
    hit = {"id": "abc", "ie_key": "Youtube", "title": "T", "url": "u", "channel": "C"}
    with patch.object(youtube, "run_ytdl_flat_search", return_value=hit) as search:
        ref = await client.find("some song")

    search.assert_called_once_with("some song")
    assert ref == youtube.VideoRef(
        audio_key="youtube/abc", url="u", title="T", channel="C"
    )


@pytest.mark.asyncio
async def test_find_search_without_results(client):
    with patch.object(youtube, "run_ytdl_flat_search", return_value=None):
        assert await client.find("zzz") is None


@pytest.mark.asyncio
async def test_extract_builds_video_info(client):
    info = {
        "id": "abc",
        "extractor_key": "Youtube",
        "title": "Pink Floyd - Money (Official Video)",
        "url": "stream",
        "webpage_url": "page",
        "duration": 382,
    }
    with patch.object(youtube, "run_ytdl", return_value=info):
        video = await client.extract("q")

    assert video is not None
    assert (video.audio_key, video.url, video.stream_url) == (
        "youtube/abc",
        "page",
        "stream",
    )
    assert (video.hint_title, video.hint_artist) == ("Money", "Pink Floyd")
    assert not video.is_stale


def test_importing_creates_no_ytdl_instances():
    # yt-dlp instances are created lazily, per process, on first use
    assert youtube._ytdl.cache_info().currsize == 0
    assert youtube._ytdl_flat.cache_info().currsize == 0
