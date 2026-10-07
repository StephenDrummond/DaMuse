"""Apply one migration file to the database configured in .env.

    poetry run python -m db.migrate docs/db/migrations/003_spotify_seeding.sql

Uses the same connection settings as the bot (DATABASE_URL, or IAM auth via
DB_*), so no psql install is needed. The migrations in docs/db/migrations are
written to be safe to re-run.
"""

import asyncio
import pathlib
import sys

from config import Settings
from db.db import Database


async def apply(path: pathlib.Path) -> None:
    db = Database(Settings.from_env().database)
    await db.init_pool()
    try:
        # one simple-query round trip; the file's own BEGIN/COMMIT make it atomic
        await db.execute(path.read_text(encoding="utf-8"))
        print(f"Applied {path.name}")
    finally:
        await db.close()


if __name__ == "__main__":
    if len(sys.argv) != 2 or not pathlib.Path(sys.argv[1]).is_file():
        sys.exit("usage: python -m db.migrate <migration .sql file>")
    asyncio.run(apply(pathlib.Path(sys.argv[1])))
