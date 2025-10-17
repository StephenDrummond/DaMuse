# test_dbclient.py
import pytest
from unittest.mock import AsyncMock
from utils.db_client import DBClient


@pytest.fixture
def dbclient():
    client = DBClient()
    client.db = AsyncMock()  # Mock the Database object
    return client


@pytest.mark.asyncio
async def test_get_user_id_returns_correct_id(dbclient):
    # Arrange
    dbclient.db.fetch_val.return_value = 42
    discord_id = 12345

    # Act
    user_id = await dbclient.get_user_id(discord_id)

    # Assert
    dbclient.db.fetch_val.assert_awaited_once()
    assert user_id == 42


@pytest.mark.asyncio
async def test_insert_if_not_exists_executes_correct_query(dbclient):
    # Arrange
    table = "users"
    columns = ["discord_id", "username"]
    values = (12345, "testuser")

    # Act
    await dbclient.insert_if_not_exists(table, columns, *values)

    # Assert
    dbclient.db.execute.assert_awaited_once()
    called_query = dbclient.db.execute.call_args[0][0]
    assert "INSERT INTO users" in called_query
    assert "ON CONFLICT" in called_query


@pytest.mark.asyncio
async def test_upsert_preferences_executes_upsert_correctly(dbclient):
    # Arrange
    table = "preferences"
    key_columns = ["user_id", "song_id"]
    update_columns = ["preference_score", "last_played"]
    values = (1, 2, 0.5, "2025-10-15")

    # Act
    await dbclient.upsert_preferences(table, key_columns, update_columns, *values)

    # Assert
    dbclient.db.execute.assert_awaited_once()
    called_query = dbclient.db.execute.call_args[0][0]
    assert "ON CONFLICT" in called_query
    assert "DO UPDATE" in called_query
    assert "preference_score" in called_query
