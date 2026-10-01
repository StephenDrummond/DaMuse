from unittest.mock import patch

import pytest

from api.spotify import get_spotify_info  # updated to your module

# Sample mock data
mock_artist_result = {
    "artists": {
        "items": [
            {
                "name": "Pink Floyd",
                "id": "artist_id_1",
                "genres": ["progressive rock", "classic rock"],
                "followers": {"total": 1000000},
                "external_urls": {"spotify": "https://spotify.com/artist"},
                "uri": "spotify:artist:artist_id_1",
            }
        ]
    }
}

mock_artist_top_tracks = {"tracks": [{"name": f"Track {i}"} for i in range(5)]}

mock_track_result = {
    "tracks": {
        "items": [
            {
                "name": "Money",
                "artists": [{"id": "artist_id_2", "name": "Pink Floyd"}],
                "album": {"name": "The Wall", "release_date": "1973-03-01"},
                "duration_ms": 382000,
                "popularity": 85,
                "external_urls": {"spotify": "https://spotify.com/track"},
                "uri": "spotify:track:track_id_1",
                "preview_url": "https://preview.url",
            }
        ]
    }
}

mock_track_artist_info = {
    "name": "Pink Floyd",
    "genres": ["progressive rock", "classic rock"],
}


@pytest.mark.asyncio
async def test_artist_query_returns_artist():
    with (
        patch("api.spotify.sp.search", return_value=mock_artist_result),
        patch("api.spotify.sp.artist_top_tracks", return_value=mock_artist_top_tracks),
    ):
        info = await get_spotify_info("Pink Floyd")
        assert info is not None
        assert info["type"] == "artist"
        assert info["name"] == "Pink Floyd"
        assert len(info["top_tracks"]) == 5


@pytest.mark.asyncio
async def test_track_query_returns_track():
    with (
        patch("api.spotify.sp.search") as mock_search,
        patch("api.spotify.sp.artist", return_value=mock_track_artist_info),
    ):
        # Return track result only if query matches
        mock_search.return_value = mock_track_result

        info = await get_spotify_info("Money Pink Floyd")
        assert info is not None
        assert info["type"] == "track"
        assert info["name"] == "Money"
        assert info["artists"] == ["Pink Floyd"]
        assert info["genres"] == ["progressive rock", "classic rock"]


@pytest.mark.asyncio
async def test_nonexistent_query_returns_none():
    with patch(
        "api.spotify.sp.search",
        return_value={"artists": {"items": []}, "tracks": {"items": []}},
    ):
        info = await get_spotify_info("Nonexistent Song 12345")
        assert info is None


@pytest.mark.parametrize(
    "text, expected",
    [
        (
            "https://open.spotify.com/track/4uLU6hMCjMI75M1A2tKUQC",
            "4uLU6hMCjMI75M1A2tKUQC",
        ),
        (
            "https://open.spotify.com/intl-de/track/4uLU6hMCjMI75M1A2tKUQC?si=x",
            "4uLU6hMCjMI75M1A2tKUQC",
        ),
        ("https://open.spotify.com/album/1", None),
        ("pink floyd money", None),
    ],
)
def test_spotify_track_id(text, expected):
    from api.spotify import spotify_track_id

    assert spotify_track_id(text) == expected


@pytest.mark.asyncio
async def test_get_track_title_artist():
    from api.spotify import get_track_title_artist

    track = {"name": "Money", "artists": [{"name": "Pink Floyd"}, {"name": "X"}]}
    with patch("api.spotify.sp.track", return_value=track):
        assert await get_track_title_artist("id") == ("Money", "Pink Floyd")
