import pytest
from unittest.mock import patch, AsyncMock

from api.spotify import search_artist, search_track, get_spotify_info  # replace 'api.spotify' with your file name


@pytest.mark.asyncio
@patch("api.spotify.sp.search")
@patch("api.spotify.sp.artist_top_tracks")
async def test_search_artist(mock_top_tracks, mock_search):
    # Mock artist search result
    mock_search.return_value = {
        "artists": {
            "items": [{
                "id": "123",
                "name": "Pink Floyd",
                "genres": ["rock", "psychedelic rock"],
                "followers": {"total": 1000000},
                "external_urls": {"spotify": "https://spotify.com/pinkfloyd"},
                "uri": "spotify:artist:123"
            }]
        }
    }

    # Mock top tracks
    mock_top_tracks.return_value = {
        "tracks": [{"name": "Money"}, {"name": "Time"}]
    }

    result = await search_artist("Pink Floyd")
    assert result is not None
    assert result["name"] == "Pink Floyd"
    assert "Money" in result["top_tracks"]


@pytest.mark.asyncio
@patch("api.spotify.sp.search")
@patch("api.spotify.sp.artist")
async def test_search_track(mock_artist, mock_search):
    # Mock track search result
    mock_search.return_value = {
        "tracks": {
            "items": [{
                "id": "track123",
                "name": "Money",
                "artists": [{"id": "123", "name": "Pink Floyd"}],
                "album": {"name": "The Dark Side of the Moon", "release_date": "1973-03-01"},
                "duration_ms": 382000,
                "popularity": 90,
                "external_urls": {"spotify": "https://spotify.com/money"},
                "uri": "spotify:track:track123",
                "preview_url": "https://preview.spotify.com/money.mp3"
            }]
        }
    }

    mock_artist.return_value = {
        "genres": ["rock", "psychedelic rock"],
        "name": "Pink Floyd"
    }

    result = await search_track("Money")
    assert result is not None
    assert result["name"] == "Money"
    assert "Pink Floyd" in result["artists"]
    assert "rock" in result["genres"]


@pytest.mark.asyncio
@patch("api.spotify.search_artist", new_callable=AsyncMock)
@patch("api.spotify.search_track", new_callable=AsyncMock)
async def test_get_spotify_info_artist_found(mock_track, mock_artist):
    # Only artist found
    mock_artist.return_value = {"type": "artist", "name": "Pink Floyd"}
    mock_track.return_value = None

    result = await get_spotify_info("Pink Floyd")
    assert result["type"] == "artist"


@pytest.mark.asyncio
@patch("api.spotify.search_artist", new_callable=AsyncMock)
@patch("api.spotify.search_track", new_callable=AsyncMock)
async def test_get_spotify_info_track_found(mock_track, mock_artist):
    # Artist not found, track found
    mock_artist.return_value = None
    mock_track.return_value = {"type": "track", "name": "Money"}

    result = await get_spotify_info("Money")
    assert result["type"] == "track"


@pytest.mark.asyncio
@patch("api.spotify.search_artist", new_callable=AsyncMock)
@patch("api.spotify.search_track", new_callable=AsyncMock)
async def test_get_spotify_info_none_found(mock_track, mock_artist):
    # Neither artist nor track found
    mock_artist.return_value = None
    mock_track.return_value = None

    result = await get_spotify_info("Unknown")
    assert result is None
