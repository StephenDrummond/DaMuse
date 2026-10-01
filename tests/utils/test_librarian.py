from unittest.mock import AsyncMock

import pytest

from utils.librarian import Librarian, TrackIds


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
async def test_add_members_batches_in_one_call(librarian, mock_db):
    await librarian.add_members_to_db([(1, "a"), (2, "b")])

    mock_db.batch_insert.assert_awaited_once()
    assert mock_db.batch_insert.await_args.args[1] == [(1, "a"), (2, "b")]


@pytest.mark.asyncio
async def test_add_members_empty_is_noop(librarian, mock_db):
    await librarian.add_members_to_db([])

    mock_db.batch_insert.assert_not_awaited()


@pytest.mark.asyncio
async def test_register_track_returns_ids(db, conn):
    conn.fetchval.side_effect = [7, 42]  # artist id, then song id
    conn.fetch.return_value = [{"id": 3}, {"id": 4}]

    ids = await Librarian(db).register_track("Money", "Pink Floyd", ["rock", "prog"])

    assert ids == TrackIds(song_id=42, artist_id=7, genre_ids=[3, 4])
    # genres linked to the artist
    link_args = conn.execute.await_args.args
    assert "artist_genres" in link_args[0]
    assert link_args[1:] == (7, [3, 4])
    # song keyed on (title, artist_id)
    assert conn.fetchval.await_args_list[1].args[1:] == ("Money", 7)


@pytest.mark.asyncio
async def test_register_track_dedupes_genres(db, conn):
    conn.fetchval.side_effect = [7, 42]
    conn.fetch.return_value = [{"id": 3}]

    await Librarian(db).register_track("Song", "Artist", ["rock", "rock"])

    assert conn.fetch.await_args.args[1] == ["rock"]


@pytest.mark.asyncio
async def test_register_track_without_genres(db, conn):
    conn.fetchval.side_effect = [7, 42]

    ids = await Librarian(db).register_track("Song", "Artist", [])

    assert ids.genre_ids == []
    conn.fetch.assert_not_awaited()
    conn.execute.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("title, artist", [(None, "a"), ("t", None), (1, "a")])
async def test_register_track_invalid_types(db, title, artist):
    with pytest.raises(TypeError):
        await Librarian(db).register_track(title, artist, [])


@pytest.mark.asyncio
async def test_get_track_ids(mock_db):
    mock_db.fetch_row.return_value = {"song_id": 1, "artist_id": 2, "genre_ids": [5]}

    ids = await Librarian(mock_db).get_track_ids(1)

    assert ids == TrackIds(song_id=1, artist_id=2, genre_ids=[5])


@pytest.mark.asyncio
async def test_get_track_ids_missing(mock_db):
    mock_db.fetch_row.return_value = None

    assert await Librarian(mock_db).get_track_ids(1) is None
