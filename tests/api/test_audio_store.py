from unittest.mock import MagicMock

import pytest
from botocore.exceptions import ClientError

from api.audio_store import AudioStore, CachedAudio


@pytest.fixture
def client():
    return MagicMock()


@pytest.fixture
def store(client):
    return AudioStore("bucket", "audio/", client=client)


def client_error(code):
    return ClientError({"Error": {"Code": code}}, "HeadObject")


def test_object_key(store):
    assert store.object_key("youtube/abc") == "audio/youtube/abc.opus"


@pytest.mark.asyncio
async def test_lookup_hit_decodes_metadata(store, client):
    client.head_object.return_value = {
        "Metadata": {
            "title": "Bj%C3%B6rk%20-%20Army%20of%20Me",
            "hint-title": "Army%20of%20Me",
            "hint-artist": "Bj%C3%B6rk",
            "source-url": "https%3A//youtu.be/x",
            "duration": "235.0",
        }
    }

    cached = await store.lookup("youtube/abc")

    client.head_object.assert_called_once_with(
        Bucket="bucket", Key="audio/youtube/abc.opus"
    )
    assert cached == CachedAudio(
        key="audio/youtube/abc.opus",
        title="Björk - Army of Me",
        hint_title="Army of Me",
        hint_artist="Björk",
        source_url="https://youtu.be/x",
        duration=235.0,
    )


@pytest.mark.asyncio
async def test_lookup_hit_without_metadata_falls_back(store, client):
    client.head_object.return_value = {"Metadata": {}}

    cached = await store.lookup("youtube/abc")

    assert cached is not None
    assert cached.title == "youtube/abc"
    assert cached.hint_artist is None
    assert cached.duration is None


@pytest.mark.asyncio
@pytest.mark.parametrize("code", ["404", "NoSuchKey", "403", "500"])
async def test_lookup_errors_are_misses(store, client, code):
    client.head_object.side_effect = client_error(code)

    assert await store.lookup("youtube/abc") is None


def test_playback_url_is_presigned_get(store, client):
    client.generate_presigned_url.return_value = "https://signed"

    assert store.playback_url("audio/youtube/abc.opus") == "https://signed"
    args, kwargs = client.generate_presigned_url.call_args
    assert args == ("get_object",)
    assert kwargs["Params"] == {"Bucket": "bucket", "Key": "audio/youtube/abc.opus"}


def test_upload_quotes_metadata_and_skips_none(store, client):
    key = store.upload(
        "/tmp/a.opus",
        "youtube/abc",
        {"title": "Björk", "hint-artist": None, "duration": 235, "ignored": "x"},
    )

    assert key == "audio/youtube/abc.opus"
    path, bucket, object_key = client.upload_file.call_args.args
    assert (path, bucket, object_key) == ("/tmp/a.opus", "bucket", key)
    extra = client.upload_file.call_args.kwargs["ExtraArgs"]
    assert extra["ContentType"] == "audio/ogg"
    assert extra["Metadata"] == {"title": "Bj%C3%B6rk", "duration": "235"}
