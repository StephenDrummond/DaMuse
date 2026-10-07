"""One-off: create DaMuse's tables in the database configured in .env.

    poetry run python -m db.apply_schema

Uses the same connection settings as the bot (DATABASE_URL, or IAM auth via
DB_*), so no psql install is needed. Refuses to run against a database that
already has tables; for existing databases apply migrations/ instead.
"""

import asyncio
import pathlib
import sys

from config import Settings
from db.db import Database

SCHEMA = pathlib.Path(__file__).parents[1] / "docs" / "db" / "schema.sql"

TABLES_QUERY = (
    "SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename"
)


async def main() -> None:
    db = Database(Settings.from_env().database)
    await db.init_pool()
    try:
        existing = [row["tablename"] for row in await db.fetch(TABLES_QUERY)]
        if existing:
            sys.exit(
                f"Database already has {len(existing)} tables ({', '.join(existing)}); "
                "nothing applied. Use the files in migrations/ to update it."
            )
        # one simple-query round trip: all statements succeed or none do
        await db.execute(SCHEMA.read_text(encoding="utf-8"))
        created = [row["tablename"] for row in await db.fetch(TABLES_QUERY)]
        print(f"Created {len(created)} tables: {', '.join(created)}")
    finally:
        await db.close()


if __name__ == "__main__":
    asyncio.run(main())
