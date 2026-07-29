from unittest.mock import AsyncMock

import pytest

from utils.librarian import Librarian


@pytest.fixture
def mock_db():
    db = AsyncMock()
    return db


@pytest.fixture
def librarian(mock_db):
    return Librarian(mock_db)


@pytest.mark.asyncio
async def test_add_member_valid(librarian):
    # Test normal integer
    librarian.insert_if_not_exists = AsyncMock()
    await librarian.add_member_to_db(123, "tester")
    librarian.insert_if_not_exists.assert_awaited_once_with(
        "users", ["discord_id", "username"], 123, "tester"
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("invalid_input", ["123", 123.45, None, [], {}, object()])
async def test_add_member_invalid_type(librarian, invalid_input):
    with pytest.raises(TypeError):
        await librarian.add_member_to_db(invalid_input, "tester")


@pytest.mark.asyncio
@pytest.mark.parametrize("edge_input", [0, -1, 2**31, 2**63])
async def test_add_member_edge_values(librarian, edge_input):
    librarian.insert_if_not_exists = AsyncMock()
    await librarian.add_member_to_db(edge_input, "tester")
    librarian.insert_if_not_exists.assert_awaited_once_with(
        "users", ["discord_id", "username"], edge_input, "tester"
    )


@pytest.mark.asyncio
async def test_db_insert_failure(librarian):
    # Simulate DB insert raising an exception
    librarian.insert_if_not_exists = AsyncMock(side_effect=Exception("DB error"))
    with pytest.raises(Exception) as exc_info:
        await librarian.add_member_to_db(123, "tester")
    assert str(exc_info.value) == "DB error"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "artist_name",
    ["The Beatles", "Björk", "A" * 255, ""],  # normal, special chars, long, empty
)
async def test_add_artist_valid(librarian, artist_name):
    librarian.insert_if_not_exists = AsyncMock()
    await librarian.add_artist_to_db(artist_name)
    librarian.insert_if_not_exists.assert_awaited_once_with(
        "artists", ["name"], artist_name
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("invalid_input", [123, 12.5, None, [], {}, object()])
async def test_add_artist_invalid_type(librarian, invalid_input):
    with pytest.raises(TypeError):
        await librarian.add_artist_to_db(invalid_input)


@pytest.mark.asyncio
async def test_add_artist_db_failure(librarian):
    librarian.insert_if_not_exists = AsyncMock(side_effect=Exception("DB error"))
    with pytest.raises(Exception) as exc_info:
        await librarian.add_artist_to_db("Test Artist")
    assert str(exc_info.value) == "DB error"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "title, artist_id",
    [
        ("Yesterday", 1),
        ("Björk Song", 0),
        ("A" * 255, 2**31),  # long title, large artist ID
        ("", 5),  # empty string
    ],
)
async def test_add_songs_valid(librarian, title, artist_id):
    librarian.insert_if_not_exists = AsyncMock()
    await librarian.add_songs_to_db(title, artist_id)
    librarian.insert_if_not_exists.assert_awaited_once_with(
        "songs",
        ["title", "artist_id"],
        title,
        artist_id,
        conflict_columns=["title", "artist_id"],
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "title, artist_id",
    [
        (123, 1),  # title not str
        ("Song", "1"),  # artist_id not int
        (None, 1),
        ("Song", None),
        ([], 1),
        ("Song", []),
    ],
)
async def test_add_songs_invalid_type(librarian, title, artist_id):
    with pytest.raises(TypeError):
        await librarian.add_songs_to_db(title, artist_id)


@pytest.mark.asyncio
async def test_add_songs_db_failure(librarian):
    librarian.insert_if_not_exists = AsyncMock(side_effect=Exception("DB error"))
    with pytest.raises(Exception) as exc_info:
        await librarian.add_songs_to_db("Song Title", 1)
    assert str(exc_info.value) == "DB error"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "genre_name",
    [
        "Rock",
        "Hip-Hop",
        "A" * 255,
        "",
        "R&B",
        "電子音楽",  # normal, special chars, long, empty, unicode
    ],
)
async def test_add_genre_valid(librarian, genre_name):
    librarian.insert_if_not_exists = AsyncMock()
    await librarian.add_genre_to_db(genre_name)
    librarian.insert_if_not_exists.assert_awaited_once_with(
        "genres", ["name"], genre_name
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("invalid_input", [123, 12.5, None, [], {}, object()])
async def test_add_genre_invalid_type(librarian, invalid_input):
    with pytest.raises(TypeError):
        await librarian.add_genre_to_db(invalid_input)


@pytest.mark.asyncio
async def test_add_genre_db_failure(librarian):
    librarian.insert_if_not_exists = AsyncMock(side_effect=Exception("DB error"))
    with pytest.raises(Exception) as exc_info:
        await librarian.add_genre_to_db("Jazz")
    assert str(exc_info.value) == "DB error"
