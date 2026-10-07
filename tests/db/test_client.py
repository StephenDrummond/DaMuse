from unittest.mock import AsyncMock

import pytest

from db.client import DBClient


@pytest.mark.parametrize("table", list(DBClient.PREFERENCE_TABLE_MAPPING))
def test_score_update_query_targets_table(table):
    _, _, id_column = DBClient.PREFERENCE_TABLE_MAPPING[table]
    query = DBClient.build_score_update_query(table)

    assert f"INSERT INTO {table} AS t" in query
    assert f"ON CONFLICT (user_id, {id_column}) DO UPDATE" in query
    # moving average, clamped to [0, 1]
    assert "t.preference_score\n" in query or "t.preference_score " in query
    assert "GREATEST(LEAST(" in query


def test_unknown_table_raises():
    with pytest.raises(KeyError):
        DBClient.build_score_update_query("nope")


def ema(score, rate, target):
    """Python mirror of the SQL update, for checking the math."""
    return max(0.0, min(1.0, score + rate * (target - score)))


def test_moving_average_converges_and_stays_bounded():
    score = DBClient.NEUTRAL_SCORE
    for _ in range(100):
        score = ema(score, 0.3, 1.0)
    assert 0.99 < score <= 1.0

    for _ in range(100):
        score = ema(score, 0.3, 0.0)
    assert 0.0 <= score < 0.01


@pytest.mark.asyncio
async def test_insert_if_not_exists_composite_conflict():
    db = AsyncMock()

    await DBClient(db).insert_if_not_exists(
        "songs", ["title", "artist_id"], "t", 1, conflict_columns=["title", "artist_id"]
    )

    query = db.execute.await_args.args[0]
    assert "ON CONFLICT (title, artist_id) DO NOTHING" in query
    assert db.execute.await_args.args[1:] == ("t", 1)
