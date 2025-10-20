from unittest.mock import patch, AsyncMock, ANY

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

    return p


# Fixture to patch get_spotify_info for all tests that use it
@pytest.fixture
def mock_get_spotify_info():
    with patch("utils.profiler.get_spotify_info", new_callable=AsyncMock) as mock_func:
        mock_func.return_value = {
            "name": "Comfortably Numb",
            "artists": ["Pink Floyd"],
            "genres": ["progressive rock", "classic rock"],
        }
        yield mock_func


# Fixture for a mock Discord member
@pytest.fixture
def mock_member():
    return MockMember(id=12345)


# fixture for mock id
@pytest.fixture
def mock_id():
    return 12345


# Fixture for a sample song name
@pytest.fixture
def song_name():
    return "Comfortably Numb"


# Fixture for alpha value
@pytest.fixture
def alpha():
    return 0.5


# Fixture for liked value
@pytest.fixture
def liked():
    return True


# Fixture for song_info
@pytest.fixture
def song_info():
    return SongInfo(
        name="Money",
        artists=["Pink Floyd"],
        genres=["progressive rock", "classic rock"],
    )


@pytest.mark.asyncio
async def test_log_event_calls_get_spotify_info(
    profiler, mock_member, song_name, alpha, liked, mock_get_spotify_info
):
    await profiler.log_event(mock_member, song_name, alpha, liked)
    mock_get_spotify_info.assert_awaited_once_with(song_name)


@pytest.mark.asyncio
async def test_log_event_calls__log_preference_group_correctly(
    profiler, mock_member, song_name, alpha, liked, mock_get_spotify_info
):
    # arrange
    profiler._log_preference_group = AsyncMock()

    # act
    await profiler.log_event(mock_member, song_name, alpha, liked)
    args, _ = profiler._log_preference_group.call_args
    member_id_arg, song_info_arg, alpha_arg, liked_arg = args

    # assert
    assert member_id_arg == mock_member.id

    assert isinstance(song_info_arg, SongInfo)
    assert song_info_arg.name == "Comfortably Numb"
    assert song_info_arg.artists == ["Pink Floyd"]
    assert song_info_arg.genres == ["progressive rock", "classic rock"]

    assert alpha_arg == alpha
    assert liked_arg == liked


@pytest.mark.asyncio
async def test_log_event_handles_get_spotify_info_none(
    profiler, mock_member, song_name, alpha, liked
):
    # arrange
    profiler._log_preference_group = AsyncMock()

    # Patch get_spotify_info to return None (simulate failure)
    with patch(
        "utils.profiler.get_spotify_info", new_callable=AsyncMock
    ) as mock_get_info:
        mock_get_info.return_value = None
        # Call log_event
        await profiler.log_event(mock_member, song_name, alpha, liked)

        # _log_preference_group should not be called because there is no song info
        profiler._log_preference_group.assert_not_awaited()


@pytest.mark.asyncio
async def test__log_preference_group_calls_log_preference(
    profiler, mock_id, song_info, alpha, liked
):
    profiler.log_preference = AsyncMock()

    await profiler._log_preference_group(mock_id, song_info, alpha, liked)

    # 1 song + 1 artist + 5 genres = 4 calls
    assert profiler.log_preference.await_count == 1 + len(song_info.artists) + len(
        song_info.genres
    )

    # 1 call per input
    profiler.log_preference.assert_any_await(
        "song_user_likes", song_info.name, mock_id, alpha, liked
    )
    profiler.log_preference.assert_any_await(
        "artist_user_likes", song_info.artists[0], mock_id, alpha, liked
    )
    for genre in song_info.genres:
        profiler.log_preference.assert_any_await(
            "genre_user_likes", genre, mock_id, alpha, liked
        )


@pytest.mark.asyncio
async def test__log_preference_group_handles_failure(
    profiler, mock_id, song_info, alpha, liked
):
    profiler.db.execute.side_effect = Exception("Database error")

    with patch("utils.profiler.logger.exception") as mock_logger:
        await profiler._log_preference_group(mock_id, song_info, alpha, liked)

        assert mock_logger.called
        for call in mock_logger.call_args_list:
            print(call[0][0])


@pytest.mark.asyncio
async def test_log_preference_db_exception_logs_exception(
    profiler, mock_id, song_info, alpha, liked
):
    profiler.db.fetch_val = AsyncMock(side_effect=Exception("Database error"))

    with patch("utils.profiler.logger.exception") as mock_logger:
        await profiler._log_preference_group(mock_id, song_info, alpha, liked)

        assert mock_logger.called
        for msg in mock_logger.call_args_list:
            assert "Database error" in msg[0][0]


@pytest.mark.asyncio
async def test__log_preference_group_target_id_none(
    profiler, mock_id, song_info, alpha, liked
):
    profiler.db.fetch_val = AsyncMock(return_value=None)

    with patch("utils.profiler.logger.exception") as mock_logger:
        await profiler._log_preference_group(mock_id, song_info, alpha, liked)

        assert mock_logger.called
        for call in mock_logger.call_args_list:
            print(call[0][0])


@pytest.mark.asyncio
async def test_log_preference_target_id_none_logs_exception(
    profiler, mock_id, song_info, alpha, liked
):
    profiler.db.fetch_val = AsyncMock(return_value=None)

    with patch("utils.profiler.logger.exception") as mock_logger:
        await profiler._log_preference_group(mock_id, song_info, alpha, liked)

        assert mock_logger.called

        for msg in mock_logger.call_args_list:
            logged_msg = msg[0][0]
            assert "No target_id found" in str(logged_msg)


@pytest.mark.asyncio
async def test_log_preference_calls_upsert_preference_in_db(
    profiler, mock_id, song_info, alpha, liked
):
    profiler.upsert_preference_in_db = AsyncMock()
    profiler.db.fetch_val = AsyncMock(return_value=67890)

    await profiler.log_preference(
        "song_user_likes", song_info.name, mock_id, alpha, liked
    )

    profiler.upsert_preference_in_db.assert_awaited_once_with(
        table_name="song_user_likes",
        user_id=mock_id,
        target_id=67890,
        liked_at=ANY,  # datetime.today() is dynamic
        foreign_table_id="song_id",
        alpha=alpha,
        liked=liked,
    )
