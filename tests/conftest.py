from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.fixture
def conn():
    """The connection handed out inside `async with db.transaction()`."""
    return AsyncMock()


@pytest.fixture
def db(conn):
    """A Database stand-in: plain query methods are AsyncMocks, and
    `transaction()` is an async context manager yielding `conn`."""
    db = AsyncMock()

    @asynccontextmanager
    async def transaction():
        yield conn

    db.transaction = MagicMock(side_effect=transaction)
    return db
