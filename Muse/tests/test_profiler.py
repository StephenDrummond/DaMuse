import pytest
import asyncio
from unittest.mock import AsyncMock, patch
from datetime import datetime

from utils.profiler import Profiler, SongInfo

# -----------------------------
# Required for async test support
# -----------------------------
pytestmark = pytest.mark.asyncio


@pytest.fixture
def profiler():
    # Create a profiler instance with mocked DB
    p = Profiler()
    p.db = AsyncMock()
    # Also mock upsert_preferences so we can verify calls
    p.upsert_preferences = AsyncMock()
    return p


async def test_log_preference_calls_upsert(profiler):
    # Mock fetch_val to return a fake target_id
    profiler.db.fetch_val.return_value = 42

    # Call log_preference
    await profiler.log_preference(
        table_name="song_user_likes",
        target_name="Test Song",
        member_id=64,
        alpha=0.2,
        liked=True,
    )

    # Assert fetch_val was called correctly
    profiler.db.fetch_val.assert_awaited_with(
        "SELECT id FROM songs WHERE title = $1", "Test Song"
    )

    # Assert upsert_preferences was called
    profiler.upsert_preferences.assert_awaited()


async def test_log_event_creates_all_preferences(profiler):
    # Patch get_spotify_info to return predictable metadata
    with patch("utils.profiler.get_spotify_info", new_callable=AsyncMock) as mock_info:
        mock_info.return_value = {
            "name": "Test Song",
            "artists": ["Test Artist"],
            "genres": ["rock", "pop"],
        }

        # Fake Discord member
        class FakeMember:
            id = 123

        await profiler.log_event(FakeMember(), "Test Song", alpha=0.3, liked=True)

        # Assert upsert_preferences was called 1 (song) + 1 (artist) + 2 (genres) = 4 times
        assert profiler.upsert_preferences.await_count == 4


async def test_upsert_preference_in_db_calls_upsert(profiler):
    liked_at = datetime.now()

    await profiler.upsert_preference_in_db(
        table_name="song_user_likes",
        user_id=1,
        target_id=99,
        liked_at=liked_at,
        target_column="song_id",
        alpha=0.4,
        liked=True,
    )

    profiler.upsert_preferences.assert_awaited_once()
