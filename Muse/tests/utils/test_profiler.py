from datetime import datetime
from unittest.mock import AsyncMock, patch, MagicMock

import pytest

from utils.profiler import Profiler, SongInfo


@pytest.fixture
def profiler():
    db_mock = AsyncMock()
    return Profiler(db=db_mock)


@pytest.mark.asyncio
async def test_log_event_skips_if_no_spotify_info(profiler):
    """If get_spotify_info returns None, nothing else should run."""
    member_mock = MagicMock()
    with patch(
        "utils.profiler.get_spotify_info", new_callable=AsyncMock
    ) as mock_spotify:
        mock_spotify.return_value = None
        profiler._log_preference_group = AsyncMock()

        await profiler.log_event(member_mock, "song_name", 0.5, True)
        profiler._log_preference_group.assert_not_awaited()


@pytest.mark.asyncio
async def test_log_event_calls_log_preference_group(profiler):
    """Ensure _log_preference_group is called with correct SongInfo."""
    member_mock = MagicMock()
    fake_info = {
        "name": "song_name",
        "artists": ["artist_name"],
        "genres": ["pop", "rock"],
    }
    with patch(
        "utils.profiler.get_spotify_info", new_callable=AsyncMock
    ) as mock_spotify:
        mock_spotify.return_value = fake_info
        profiler._log_preference_group = AsyncMock()

        await profiler.log_event(member_mock, "song_name", 0.8, False)

        profiler._log_preference_group.assert_awaited_once()
        args, kwargs = profiler._log_preference_group.call_args
        assert args[0] == member_mock.id
        assert isinstance(args[1], SongInfo)
        assert args[1].name == "song_name"
        assert args[1].artists == ["artist_name"]
        assert args[1].genres == ["pop", "rock"]
        assert args[2] == 0.8
        assert args[3] is False


@pytest.mark.asyncio
async def test_log_preference_group_logs_all_preferences(profiler):
    """_log_preference_group should call log_preference for song, artist,
    and each genre."""
    song_info = SongInfo(name="song", artists=["artist"], genres=["pop", "rock"])
    profiler.log_preference = AsyncMock()

    await profiler._log_preference_group(1, song_info, 0.7, True)

    # Should be called 4 times: 1 song + 1 artist + 2 genres
    assert profiler.log_preference.await_count == 4
    calls = [call.args[0] for call in profiler.log_preference.await_args_list]
    assert "song_user_likes" in calls
    assert "artist_user_likes" in calls
    assert "genre_user_likes" in calls


@pytest.mark.asyncio
async def test_log_preference_handles_value_error(profiler):
    """log_preference should catch ValueError from get_target_id."""
    profiler.get_target_id = AsyncMock(side_effect=ValueError("Not found"))
    profiler.safe_upsert_preference = AsyncMock()

    with patch("utils.profiler.logger.warning") as mock_warning:
        await profiler.log_preference("song_user_likes", "song", 1, 0.5, True)
        profiler.safe_upsert_preference.assert_not_called()
        # Check that the call argument is a ValueError instance with correct message
        called_arg = mock_warning.call_args[0][0]
        assert isinstance(called_arg, ValueError)
        assert str(called_arg) == "Not found"


@pytest.mark.asyncio
async def test_log_preference_calls_safe_upsert_with_correct_args(profiler):
    """log_preference should call safe_upsert_preference with the expected arguments."""
    profiler.get_target_id = AsyncMock(return_value=42)
    profiler.safe_upsert_preference = AsyncMock()

    await profiler.log_preference("song_user_likes", "song", 1, 0.9, False)

    profiler.safe_upsert_preference.assert_awaited_once()
    args = profiler.safe_upsert_preference.await_args[0]
    assert args[0] == "song_user_likes"  # table
    assert args[1] == ["user_id", "song_id"]  # columns
    assert args[2] == ["liked_at", "preference_score", "liked"]
    assert args[3] == 1  # member_id
    assert args[4] == 42  # target_id
    assert isinstance(args[5], datetime)  # datetime.today() passed
    assert args[6] == 0.9
    assert args[7] is False


@pytest.mark.asyncio
async def test_log_preference_group_logs_song_and_artist(profiler):
    song_info = SongInfo(name="Song A", artists=["Artist A"], genres=[])
    profiler.log_preference = AsyncMock()

    await profiler._log_preference_group(
        member_id=1, song_info=song_info, alpha=0.5, liked=True
    )

    calls = profiler.log_preference.await_args_list
    table_names = [call.args[0] for call in calls]

    assert "song_user_likes" in table_names
    assert "artist_user_likes" in table_names
    assert "genre_user_likes" not in table_names


@pytest.mark.asyncio
async def test_log_preference_group_logs_genres(profiler):
    song_info = SongInfo(name="Song B", artists=["Artist B"], genres=["Pop", "Rock"])
    profiler.log_preference = AsyncMock()

    await profiler._log_preference_group(
        member_id=2, song_info=song_info, alpha=0.7, liked=False
    )

    calls = profiler.log_preference.await_args_list
    genre_calls = [call for call in calls if call.args[0] == "genre_user_likes"]

    assert len(genre_calls) == len(song_info.genres)
    for call, genre in zip(genre_calls, song_info.genres):
        assert call.args[1] == genre


@pytest.mark.asyncio
async def test_log_preference_group_handles_empty_genres(profiler):
    song_info = SongInfo(name="Song C", artists=["Artist C"], genres=[])
    profiler.log_preference = AsyncMock()

    await profiler._log_preference_group(
        member_id=3, song_info=song_info, alpha=0.3, liked=True
    )

    calls = profiler.log_preference.await_args_list
    assert all(call.args[0] != "genre_user_likes" for call in calls)


@pytest.mark.asyncio
async def test_log_preference_group_uses_correct_alpha_and_liked(profiler):
    song_info = SongInfo(name="Song D", artists=["Artist D"], genres=["Jazz"])
    profiler.log_preference = AsyncMock()
    alpha = 0.9
    liked = False

    await profiler._log_preference_group(
        member_id=4, song_info=song_info, alpha=alpha, liked=liked
    )

    for call in profiler.log_preference.await_args_list:
        assert call.args[3] == alpha
        assert call.args[4] == liked


@pytest.mark.asyncio
async def test_log_preference_group_multiple_artists_only_logs_first(profiler):
    song_info = SongInfo(name="Song E", artists=["Artist X", "Artist Y"], genres=[])
    profiler.log_preference = AsyncMock()

    await profiler._log_preference_group(
        member_id=5, song_info=song_info, alpha=0.1, liked=True
    )

    artist_call = next(
        call
        for call in profiler.log_preference.await_args_list
        if call.args[0] == "artist_user_likes"
    )
    assert artist_call.args[1] == "Artist X"


@pytest.mark.asyncio
async def test_log_preference_handles_value_error_gracefully(caplog):
    db_mock = AsyncMock()
    profiler = Profiler(db=db_mock)

    # Patch the methods instead of assigning directly
    with patch.object(
        profiler, "get_target_id", new_callable=AsyncMock
    ) as mock_get_target_id, patch.object(
        profiler, "safe_upsert_preference", new_callable=AsyncMock
    ) as mock_safe_upsert:
        mock_get_target_id.side_effect = ValueError("Not found")

        # Call the method
        await profiler.log_preference("song_user_likes", "Missing Song", 1, 0.5, True)

        # Ensure exception is logged but does not propagate
        assert any("Not found" in record.message for record in caplog.records)
        mock_safe_upsert.assert_not_awaited()


@pytest.mark.asyncio
async def test_log_preference_with_invalid_table_name_raises_key_error():
    db_mock = AsyncMock()
    profiler = Profiler(db=db_mock)

    # Patch methods instead of assigning directly
    with patch.object(profiler, "get_target_id", new_callable=AsyncMock), patch.object(
        profiler, "safe_upsert_preference", new_callable=AsyncMock
    ):
        # This should still raise KeyError for invalid table
        with pytest.raises(KeyError):
            await profiler.log_preference("invalid_table", "Item", 1, 0.5, True)


@pytest.mark.asyncio
async def test_log_preference_accepts_empty_target_name():
    db_mock = AsyncMock()
    profiler = Profiler(db=db_mock)

    # Patch methods instead of assigning directly
    with patch.object(
        profiler, "get_target_id", new_callable=AsyncMock
    ) as mock_get_target_id, patch.object(
        profiler, "safe_upsert_preference", new_callable=AsyncMock
    ) as mock_safe_upsert:
        mock_get_target_id.return_value = 1

        await profiler.log_preference("song_user_likes", "", 1, 0.0, False)

        mock_get_target_id.assert_awaited_once_with("songs", "name", "")
        mock_safe_upsert.assert_awaited_once()
