"""Integration tests against a real Postgres.

Set TEST_DATABASE_URL to a *disposable* database, e.g.
postgresql://postgres:postgres@localhost:5432/damuse_test. Its public schema is
dropped and rebuilt from schema.sql once per session, and every table is
truncated before each test. Without the variable these tests are skipped.
"""

import asyncio
import os
import pathlib
from urllib.parse import urlparse

import asyncpg
import pytest
import pytest_asyncio

from config import DatabaseSettings
from db.db import Database

SCHEMA = (
    pathlib.Path(__file__).parents[2]
    / "Documentation"
    / "db documentation"
    / "schema.sql"
)
TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")

HERE = pathlib.Path(__file__).parent


def pytest_collection_modifyitems(config, items):
    """Mark everything under tests/integration, and skip it without a DB."""
    skip = pytest.mark.skip(reason="TEST_DATABASE_URL not set")
    for item in items:
        if HERE in pathlib.Path(item.path).parents:
            item.add_marker(pytest.mark.integration)
            if not TEST_DATABASE_URL:
                item.add_marker(skip)


async def _rebuild_schema(url: str) -> None:
    connection = await asyncpg.connect(url)
    try:
        await connection.execute("DROP SCHEMA public CASCADE; CREATE SCHEMA public;")
        await connection.execute(SCHEMA.read_text(encoding="utf-8"))
    finally:
        await connection.close()


@pytest.fixture(scope="session")
def database_url() -> str:
    assert TEST_DATABASE_URL is not None
    # this wipes the database: refuse anything that isn't obviously a test one
    name = urlparse(TEST_DATABASE_URL).path.lstrip("/")
    if "test" not in name:
        pytest.exit(f"Refusing to wipe {name!r}: TEST_DATABASE_URL must name a test DB")
    asyncio.run(_rebuild_schema(TEST_DATABASE_URL))
    return TEST_DATABASE_URL


@pytest_asyncio.fixture
async def pg(database_url):
    """A real Database (plain DSN, no IAM) on an empty, freshly-truncated schema."""
    db = Database(DatabaseSettings(dsn=database_url, pool_min_size=1, pool_max_size=5))
    await db.init_pool()
    tables = await db.fetch(
        "SELECT tablename FROM pg_tables WHERE schemaname = 'public'"
    )
    await db.execute(
        "TRUNCATE "
        + ", ".join(row["tablename"] for row in tables)
        + " RESTART IDENTITY CASCADE"
    )
    yield db
    await db.close()
