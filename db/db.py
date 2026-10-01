import asyncio
import logging
import os
import ssl
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, Optional, List

import asyncpg
import boto3
from asyncpg import Record
from asyncpg.pool import Pool
from dotenv import load_dotenv

load_dotenv()

DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
AWS_REGION = os.getenv("AWS_REGION", "us-east-2")
# Path to the RDS CA bundle (https://truststore.pki.rds.amazonaws.com/global/
# global-bundle.pem). When set, the server certificate is fully verified.
DB_SSL_ROOT_CERT = os.getenv("DB_SSL_ROOT_CERT")
# Keep (shard processes x max size) under the cluster's connection limit, or
# put RDS Proxy in front of Aurora once running more than a few processes.
DB_POOL_MIN_SIZE = int(os.getenv("DB_POOL_MIN_SIZE", "3"))
DB_POOL_MAX_SIZE = int(os.getenv("DB_POOL_MAX_SIZE", "20"))

logger = logging.getLogger(__name__)

# boto3 picks up AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY / AWS_SESSION_TOKEN
# from the environment automatically (load_dotenv() above already populated
# them from .env if present), falling back to ~/.aws/credentials or an
# attached IAM role. No credentials are handled explicitly here.
_rds_client = boto3.client("rds", region_name=AWS_REGION)


def _sign_auth_token() -> str:
    """Sign a short-lived (~15 min) IAM auth token for RDS/Aurora login."""
    return _rds_client.generate_db_auth_token(
        DBHostname=DB_HOST,
        Port=DB_PORT,
        DBUsername=DB_USER,
        Region=AWS_REGION,
    )


async def _get_auth_token() -> str:
    """Credential provider passed to asyncpg as `password`.

    asyncpg calls this for every new physical connection it opens (not just
    once at pool creation), which is what lets a 15-minute-lived IAM token
    stay valid across the pool's lifetime. Signing is local SigV4 signing
    (no network round trip) but still runs off the event loop on principle.
    """
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _sign_auth_token)


def _iam_ssl_context() -> ssl.SSLContext:
    """TLS is mandatory for IAM auth. With DB_SSL_ROOT_CERT set this matches
    sslmode='verify-full'; without it, sslmode='require' (encrypted, but the
    server certificate isn't verified)."""
    if DB_SSL_ROOT_CERT:
        return ssl.create_default_context(cafile=DB_SSL_ROOT_CERT)

    logger.warning("DB_SSL_ROOT_CERT not set; database certificate is not verified")
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


class Database:
    pool: Optional[Pool]

    def __init__(self) -> None:
        self.pool = None

    async def init_pool(self) -> None:
        """Create and store the database connection pool."""
        try:
            self.pool = await asyncpg.create_pool(
                database=DB_NAME,
                user=DB_USER,
                password=_get_auth_token,
                host=DB_HOST,
                port=DB_PORT,
                ssl=_iam_ssl_context(),
                min_size=DB_POOL_MIN_SIZE,
                max_size=DB_POOL_MAX_SIZE,
                timeout=15,
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

    async def batch_insert(self, query, rows):
        if self.pool is None:
            raise RuntimeError("Database pool not initialized")
        async with self.pool.acquire() as connection:
            await connection.executemany(query, rows)

    @asynccontextmanager
    async def transaction(self) -> AsyncIterator[asyncpg.Connection]:
        """Yield one connection with a transaction open; commits on clean exit,
        rolls back if the block raises."""
        if self.pool is None:
            raise RuntimeError("Database pool not initialized")
        async with self.pool.acquire() as connection:
            async with connection.transaction():
                yield connection

    async def close(self) -> None:
        if self.pool is not None:
            await self.pool.close()
            self.pool = None
