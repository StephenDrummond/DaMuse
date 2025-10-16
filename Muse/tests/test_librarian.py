import pytest
from unittest.mock import AsyncMock, patch

from utils.librarian import Librarian


@pytest.fixture
def librarian():
    # Create an instance of Librarian with mocked db
    lib = Librarian()
    lib.insert_if_not_exists = AsyncMock()
    return lib


@pytest.mark.asyncio
async def test_add_member_to_db_calls_insert(librarian):
    await librarian.add_member_to_db(12345)
    librarian.insert_if_not_exists.assert_awaited_once_with(
        "users", ["discord_id"], 12345
    )


@pytest.mark.asyncio
async def test_add_artist_to_db_calls_insert(librarian):
    await librarian.add_artist_to_db("Test Artist")
    librarian.insert_if_not_exists.assert_awaited_once_with(
        "artists", ["name"], "Test Artist"
    )


@pytest.mark.asyncio
async def test_add_songs_to_db_calls_insert(librarian):
    await librarian.add_songs_to_db("Test Song", 10)
    librarian.insert_if_not_exists.assert_awaited_once_with(
        "songs", ["title", "artist_id"], "Test Song", 10
    )


@pytest.mark.asyncio
async def test_add_genre_to_db_calls_insert(librarian):
    await librarian.add_genre_to_db("Rock")
    librarian.insert_if_not_exists.assert_awaited_once_with(
        "genres", ["name"], "Rock"
    )
