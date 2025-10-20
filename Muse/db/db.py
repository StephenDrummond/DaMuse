import os
from typing import Any, Optional, List

import asyncpg
from asyncpg import Record
from asyncpg.pool import Pool
from dotenv import load_dotenv

load_dotenv()

DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASS")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")


class Database:
    pool: Optional[Pool]

    def __init__(self) -> None:
        self.pool = None
        self.mongodb = None

    async def init_pool(self) -> None:
        """Create and store the database connection pool."""
        try:
            self.pool = await asyncpg.create_pool(
                database=DB_NAME,
                user=DB_USER,
                password=DB_PASSWORD,
                host=DB_HOST,
                port=DB_PORT,
                min_size=5,
                max_size=20,
            )
            print("Database pool created")
        except Exception as e:
            print("Error creating database pool:", e)

    async def execute(self, query: str, *args: Any) -> None:
        """Run a query that doesn’t return results (INSERT, UPDATE, DELETE)."""
        if self.pool is None:
            raise RuntimeError("Database pool not initialized")
        async with self.pool.acquire() as connection:
            await connection.execute(query, *args)

    async def fetch(self, query: str, *args: Any) -> List[Record]:
        """Run a query that returns multiple rows."""
        if self.pool is None:
            raise RuntimeError("Database pool not initialized")
        async with self.pool.acquire() as connection:
            return await connection.fetch(query, *args)

    async def fetch_val(self, query: str, *args: Any) -> Optional[Any]:
        """Run a query that returns a single value."""
        if self.pool is None:
            raise RuntimeError("Database pool not initialized")
        async with self.pool.acquire() as connection:
            return await connection.fetchval(query, *args)

    async def fetch_row(self, query: str, *args: Any) -> Optional[Record]:
        """Run a query that returns a single row."""
        if self.pool is None:
            raise RuntimeError("Database pool not initialized")
        async with self.pool.acquire() as connection:
            return await connection.fetchrow(query, *args)
