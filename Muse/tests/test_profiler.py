from unittest.mock import patch, AsyncMock

import pytest

from utils.profiler import Profiler, SongInfo  # Your actual module


# Sample mock for a Discord member
class MockMember:
    def __init__(self, id):
        self.id = id


# Fixture for the Profiler instance
@pytest.fixture
def profiler():
    p = Profiler(db=None)
    p.db = AsyncMock()
    p.upsert_preference_in_db = AsyncMock()
    p._log_preference_group = AsyncMock()
    return p


# Fixture for a mock Discord member
@pytest.fixture
def mock_member():
    return MockMember(id=12345)


# Fixture for a sample song name
@pytest.fixture
def song_name():
    return "Comfortably Numb"


# Fixture for Spotify info with genres
@pytest.fixture
def spotify_info_with_genres(song_name):
    return {
        "name": song_name,
        "artists": ["Pink Floyd"],
        "genres": ["Progressive Rock", "Classic Rock"]
    }


# Fixture for Spotify info missing genres (edge case)
@pytest.fixture
def spotify_info_no_genres(song_name):
    return {
        "name": song_name,
        "artists": ["Pink Floyd"]
        # genres missing
    }


# Fixture for alpha value
@pytest.fixture
def alpha():
    return 0.5


# Fixture for liked value
@pytest.fixture
def liked():
    return True


@pytest.mark.asyncio
async def test_log_event_calls_get_spotify_info_once(profiler, mock_member, song_name, spotify_info_with_genres, alpha,
                                                     liked):
    # Patch get_spotify_info and assign the mock to a variable
    with patch("utils.profiler.get_spotify_info", new_callable=AsyncMock) as mock_get_info:
        mock_get_info.return_value = spotify_info_with_genres

        # act
        await profiler.log_event(mock_member, song_name, alpha, liked)

        # Assert the mock was awaited with the correct argument
        mock_get_info.assert_awaited_once_with(song_name)


@pytest.mark.asyncio
async def test_log_event_creates_songinfo(profiler, mock_member, song_name, alpha, liked, spotify_info_with_genres):
    # Patch get_spotify_info to return predictable info
    with patch("utils.profiler.get_spotify_info", new_callable=AsyncMock) as mock_get_info:
        mock_get_info.return_value = spotify_info_with_genres

        # Call the method
        await profiler.log_event(mock_member, song_name, alpha, liked)

        # Grab the SongInfo object passed to _log_preference_group
        args, kwargs = profiler._log_preference_group.call_args
        song_info_arg = args[1]

        # Assert SongInfo is correct
        assert isinstance(song_info_arg, SongInfo)
        assert song_info_arg.name == spotify_info_with_genres["name"]
        assert song_info_arg.artists == spotify_info_with_genres["artists"]
        assert song_info_arg.genres == spotify_info_with_genres["genres"]


@pytest.mark.asyncio
async def test_log_event_calls_log_preference_group_correctly(profiler, mock_member, song_name, alpha, liked,
                                                              spotify_info_with_genres):
    with patch("utils.profiler.get_spotify_info", new_callable=AsyncMock) as mock_get_info:
        mock_get_info.return_value = spotify_info_with_genres

        # Call the method
        await profiler.log_event(mock_member, song_name, alpha, liked)

        # Grab the arguments passed to _log_preference_group
        args, kwargs = profiler._log_preference_group.call_args

        # Assert _log_preference_group called correctly
        assert args[0] == mock_member.id  # member_id
        assert args[2] == alpha  # alpha
        assert args[3] == liked  # liked
        # Ensure it was awaited
        profiler._log_preference_group.assert_awaited_once()


@pytest.mark.asyncio
async def test_log_event_handles_get_spotify_info_none(profiler, mock_member, song_name, alpha, liked):
    # Patch get_spotify_info to return None (simulate failure)
    with patch("utils.profiler.get_spotify_info", new_callable=AsyncMock) as mock_get_info:
        mock_get_info.return_value = None

        # Call log_event
        await profiler.log_event(mock_member, song_name, alpha, liked)

        # _log_preference_group should not be called because there is no song info
        profiler._log_preference_group.assert_not_awaited()
