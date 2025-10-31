import json
from unittest.mock import MagicMock, AsyncMock

import pytest

from utils.curator import Curator
from utils.observer import Observer


@pytest.fixture
def observer():
    db = AsyncMock
    obs = Observer(db)  # type: ignore
    obs.r = AsyncMock()  # mock Redis
    obs.curators = {}  # reset curators
    return obs


def test_singleton_behavior():
    db_mock = MagicMock()

    obs1 = Observer(db_mock)
    obs2 = Observer(db_mock)

    # Both instances should point to the same object
    assert (
        obs1 is obs2
    ), "Observer should return the same instance for multiple instantiations"

    # Initialization flag should be True
    assert obs1._initialized is True, "_initialized should be True after first init"
    assert (
        obs2._initialized is True
    ), "_initialized should remain True on second instantiation"

    # Ensure redis client was created only once
    assert obs1.r is obs2.r, "Redis client should be the same instance"


@pytest.mark.asyncio
async def test_cache_prefs_creates_curator(observer):
    discord_id = 123
    channel_id = 1

    # Mock fetch_preferences to return dummy rows
    observer.fetch_preferences = AsyncMock(return_value=[("item", 0.1234)])

    await observer.cache_prefs(channel_id, discord_id)

    # Check that Redis set was called for each table
    keys = [f"{channel_id}:{discord_id}:{t}" for t in ["song", "genre", "artist"]]
    assert observer.r.set.call_count == 3
    called_keys = [call[0][0] for call in observer.r.set.call_args_list]
    for key in keys:
        assert key in called_keys

    # Check that a Curator was created
    assert channel_id in observer.curators
    assert observer.curators[channel_id].member_ids == [discord_id]


@pytest.mark.asyncio
async def test_cache_prefs_adds_member_to_existing_curator(observer):
    discord_id = 456
    channel_id = 2

    # Pre-existing curator
    mock_curator = MagicMock()
    mock_curator.member_ids = [999]
    observer.curators[channel_id] = mock_curator

    observer.fetch_preferences = AsyncMock(return_value=[("item", 0.5678)])

    await observer.cache_prefs(channel_id, discord_id)

    # Check member added to existing curator
    assert discord_id in observer.curators[channel_id].member_ids


@pytest.mark.asyncio
async def test_cache_prefs_handles_empty_rows(observer):
    discord_id = 789
    channel_id = 3

    observer.fetch_preferences = AsyncMock(return_value=None)  # empty result

    await observer.cache_prefs(channel_id, discord_id)

    # Redis set should not be called
    observer.r.set.assert_not_called()

    # Curator should still be created
    assert channel_id in observer.curators
    assert observer.curators[channel_id].member_ids == [discord_id]


@pytest.mark.asyncio
async def test_load_prefs_into_memory_normal(observer):
    # mock database returning sample rows
    sample_rows = [("Song A", 0.123456), ("Song B", 0.987654)]
    observer.fetch_preferences = AsyncMock(return_value=sample_rows)

    channel_id = 1
    discord_id = 42
    table = "song_user_likes"

    await observer.load_prefs_into_memory(channel_id, discord_id, table)

    key = f"{channel_id}:{discord_id}:song"
    expected_data = json.dumps([["Song A", 0.1235], ["Song B", 0.9877]])

    observer.r.set.assert_awaited_once_with(key, expected_data)


@pytest.mark.asyncio
async def test_load_prefs_into_memory_empty(observer):
    # database returns empty list
    observer.fetch_preferences = AsyncMock(return_value=[])

    await observer.load_prefs_into_memory(1, 42, "song_user_likes")

    key = "1:42:song"
    # Redis set should be called with empty list
    observer.r.set.assert_awaited_once_with(key, json.dumps([]))


@pytest.mark.asyncio
async def test_load_prefs_into_memory_none(observer):
    # database returns None
    observer.fetch_preferences = AsyncMock(return_value=None)

    await observer.load_prefs_into_memory(1, 42, "artist_user_likes")

    # Redis set should never be called
    observer.r.set.assert_not_awaited()


@pytest.mark.asyncio
async def test_load_prefs_into_memory_raises(observer):
    # database raises an exception
    observer.fetch_preferences = AsyncMock(side_effect=Exception("DB failure"))

    with pytest.raises(Exception):
        await observer.load_prefs_into_memory(1, 42, "genre_user_likes")


@pytest.mark.asyncio
async def test_remove_cached_prefs_removes_keys_and_member(observer):
    # Setup: channel and user
    channel_id = 123
    user_id = 456

    # Mock a curator with the user_id
    mock_curator = MagicMock(spec=Curator)
    mock_curator.member_ids = [user_id]
    observer.curators[channel_id] = mock_curator

    # Call the method
    await observer.remove_cached_prefs(channel_id, user_id)

    # Redis delete called for all preference keys
    expected_calls = [
        ((f"{channel_id}:{user_id}:song",),),
        ((f"{channel_id}:{user_id}:artist",),),
        ((f"{channel_id}:{user_id}:genre",),),
    ]
    observer.r.delete.assert_has_awaits(expected_calls, any_order=True)

    # User removed from Curator
    assert user_id not in mock_curator.member_ids

    # Curator deleted since no members left
    assert channel_id not in observer.curators


@pytest.mark.asyncio
async def test_remove_cached_prefs_does_not_delete_curator_if_members_remain(observer):
    channel_id = 123
    user_id = 456

    # Curator with multiple members
    mock_curator = MagicMock(spec=Curator)
    mock_curator.member_ids = [user_id, 789]
    observer.curators[channel_id] = mock_curator

    await observer.remove_cached_prefs(channel_id, user_id)

    # Check member removed but curator still exists
    assert 456 not in mock_curator.member_ids
    assert channel_id in observer.curators


@pytest.mark.asyncio
async def test_remove_cached_prefs_channel_missing(observer):
    channel_id = 999
    user_id = 123

    # Should raise KeyError when trying to remove from non-existent channel
    with pytest.raises(KeyError):
        await observer.remove_cached_prefs(channel_id, user_id)
