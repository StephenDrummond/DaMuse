from unittest.mock import MagicMock

import pytest

from clients.spotify import SpotifyClient, spotify_track_id

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


@pytest.fixture
def sp():
    """A fake spotipy client; SpotifyClient never touches the network."""
    return MagicMock()


@pytest.fixture
def spotify(sp):
    return SpotifyClient(sp=sp)


@pytest.mark.asyncio
async def test_artist_query_returns_artist(spotify, sp):
    sp.search.return_value = mock_artist_result
    sp.artist_top_tracks.return_value = mock_artist_top_tracks

    info = await spotify.get_spotify_info("Pink Floyd")

    assert info is not None
    assert info["type"] == "artist"
    assert info["name"] == "Pink Floyd"
    assert len(info["top_tracks"]) == 5


@pytest.mark.asyncio
async def test_track_query_returns_track(spotify, sp):
    # no artist hit, so it falls through to the track search
    sp.search.side_effect = [{"artists": {"items": []}}, mock_track_result]
    sp.artist.return_value = mock_track_artist_info

    info = await spotify.get_spotify_info("Money Pink Floyd")

    assert info is not None
    assert info["type"] == "track"
    assert info["name"] == "Money"
    assert info["artists"] == ["Pink Floyd"]
    assert info["genres"] == ["progressive rock", "classic rock"]


@pytest.mark.asyncio
async def test_nonexistent_query_returns_none(spotify, sp):
    sp.search.return_value = {"artists": {"items": []}, "tracks": {"items": []}}

    assert await spotify.get_spotify_info("Nonexistent Song 12345") is None


@pytest.mark.asyncio
async def test_search_track_narrows_by_artist(spotify, sp):
    sp.search.return_value = mock_track_result
    sp.artist.return_value = mock_track_artist_info

    await spotify.search_track("Money", "Pink Floyd")

    assert sp.search.call_args.kwargs["q"] == "track:Money artist:Pink Floyd"


@pytest.mark.asyncio
async def test_errors_are_contained(spotify, sp):
    sp.search.side_effect = RuntimeError("rate limited")

    assert await spotify.get_spotify_info("x") is None


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
    assert spotify_track_id(text) == expected


@pytest.mark.asyncio
async def test_get_track_title_artist(spotify, sp):
    sp.track.return_value = {
        "name": "Money",
        "artists": [{"name": "Pink Floyd"}, {"name": "X"}],
    }

    assert await spotify.get_track_title_artist("id") == ("Money", "Pink Floyd")


def artist_item(spotify_id, name, genres=()):
    return {"id": spotify_id, "name": name, "genres": list(genres)}


@pytest.mark.asyncio
async def test_find_artist_prefers_exact_name(spotify, sp):
    sp.search.return_value = {
        "artists": {
            "items": [
                artist_item("a1", "Pink Floyd Tribute"),
                artist_item("a2", "pink floyd", ["rock"]),
            ]
        }
    }

    assert await spotify.find_artist("Pink Floyd") == {
        "id": "a2",
        "name": "pink floyd",
        "genres": ["rock"],
    }
    assert sp.search.call_args.kwargs["q"] == 'artist:"Pink Floyd"'


@pytest.mark.asyncio
async def test_find_artist_falls_back_to_top_match(spotify, sp):
    sp.search.return_value = {"artists": {"items": [artist_item("a1", "Pinkfloyd")]}}

    found = await spotify.find_artist("Pink Floyd")

    assert found is not None and found["id"] == "a1"


@pytest.mark.asyncio
async def test_find_artist_none(spotify, sp):
    sp.search.return_value = {"artists": {"items": []}}

    assert await spotify.find_artist("Nobody") is None


@pytest.mark.asyncio
async def test_get_artist(spotify, sp):
    sp.artist.return_value = artist_item("a1", "Pink Floyd", ["rock"])

    assert await spotify.get_artist("a1") == {
        "id": "a1",
        "name": "Pink Floyd",
        "genres": ["rock"],
    }


@pytest.mark.asyncio
async def test_artist_top_tracks(spotify, sp):
    sp.artist_top_tracks.return_value = {
        "tracks": [
            {"id": "t1", "name": "Money", "artists": [{"id": "a1"}]},
            {"id": "t2", "name": "Duet", "artists": [{"id": "a9"}, {"id": "a1"}]},
        ]
    }

    tracks = await spotify.artist_top_tracks("a1", market="GB")

    assert tracks == [
        {"id": "t1", "name": "Money", "artist_ids": ["a1"]},
        {"id": "t2", "name": "Duet", "artist_ids": ["a9", "a1"]},
    ]
    assert sp.artist_top_tracks.call_args.kwargs == {"country": "GB"}


@pytest.mark.asyncio
async def test_search_track_includes_spotify_ids(spotify, sp):
    sp.search.return_value = mock_track_result
    sp.artist.return_value = mock_track_artist_info

    info = await spotify.search_track("Money")

    assert info is not None
    assert info["artist_ids"] == ["artist_id_2"]
