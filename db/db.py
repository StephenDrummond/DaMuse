import asyncio
import logging
import ssl
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, Optional, List

import asyncpg
import boto3
from asyncpg import Record
from asyncpg.pool import Pool

from config import DatabaseSettings

logger = logging.getLogger(__name__)


class Database:
    """asyncpg pool wrapper.

    Two ways to connect:
    - `settings.dsn` set (local dev, tests): a plain connection string.
    - otherwise IAM auth against RDS/Aurora: no static password; a fresh
      signed token (~15-min lifetime) is generated for every new physical
      connection the pool opens. asyncpg calls the `password` callable per
      connection, which is what keeps the pool usable past the first token's
      expiry. boto3 resolves AWS credentials via its normal chain (env vars,
      ~/.aws/credentials, instance role).
    """

    pool: Optional[Pool]

    def __init__(self, settings: DatabaseSettings) -> None:
        self.settings = settings
        self.pool = None
        self._rds_client: Any = None

    async def init_pool(self) -> None:
        """Create the connection pool. Raises if the database is unreachable,
        so callers fail at startup rather than on their first query."""
        settings = self.settings
        common = dict(
            min_size=settings.pool_min_size,
            max_size=settings.pool_max_size,
            timeout=settings.connect_timeout,
        )
        if settings.dsn:
            self.pool = await asyncpg.create_pool(settings.dsn, **common)
        else:
            self._rds_client = boto3.client("rds", region_name=settings.aws_region)
            self.pool = await asyncpg.create_pool(
                database=settings.name,
                user=settings.user,
                password=self._get_auth_token,
                host=settings.host,
                port=settings.port,
                ssl=self._iam_ssl_context(),
                **common,
            )
        logger.info("Database pool created")

    def _sign_auth_token(self) -> str:
        """Sign a short-lived (~15 min) IAM auth token for RDS/Aurora login."""
        return self._rds_client.generate_db_auth_token(
            DBHostname=self.settings.host,
            Port=self.settings.port,
            DBUsername=self.settings.user,
            Region=self.settings.aws_region,
        )

    async def _get_auth_token(self) -> str:
        """Credential provider passed to asyncpg as `password`. Signing is
        local SigV4 signing (no network round trip) but still runs off the
        event loop on principle."""
        return await asyncio.to_thread(self._sign_auth_token)

    def _iam_ssl_context(self) -> ssl.SSLContext:
        """TLS is mandatory for IAM auth. With ssl_root_cert set this matches
        sslmode='verify-full'; without it, sslmode='require' (encrypted, but the
        server certificate isn't verified)."""
        if self.settings.ssl_root_cert:
            return ssl.create_default_context(cafile=self.settings.ssl_root_cert)

        logger.warning("DB_SSL_ROOT_CERT not set; database certificate is not verified")
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        return ctx

    def _require_pool(self) -> Pool:
        if self.pool is None:
            raise RuntimeError("Database pool not initialized")
        return self.pool

    async def execute(self, query: str, *args: Any) -> None:
        """Run a query that doesn’t return results (INSERT, UPDATE, DELETE)."""
        async with self._require_pool().acquire() as connection:
            await connection.execute(query, *args)

    async def fetch(self, query: str, *args: Any) -> List[Record]:
        """Run a query that returns multiple rows."""
        async with self._require_pool().acquire() as connection:
            return await connection.fetch(query, *args)

    async def fetch_val(self, query: str, *args: Any) -> Optional[Any]:
        """Run a query that returns a single value."""
        async with self._require_pool().acquire() as connection:
            return await connection.fetchval(query, *args)

    async def fetch_row(self, query: str, *args: Any) -> Optional[Record]:
        """Run a query that returns a single row."""
        async with self._require_pool().acquire() as connection:
            return await connection.fetchrow(query, *args)

    async def batch_insert(self, query, rows):
        async with self._require_pool().acquire() as connection:
            await connection.executemany(query, rows)

    @asynccontextmanager
    async def transaction(self) -> AsyncIterator[asyncpg.Connection]:
        """Yield one connection with a transaction open; commits on clean exit,
        rolls back if the block raises."""
        async with self._require_pool().acquire() as connection:
            async with connection.transaction():
                yield connection

    @asynccontextmanager
    async def connection(self) -> AsyncIterator[asyncpg.Connection]:
        """Hold one pooled connection, e.g. for LISTEN."""
        async with self._require_pool().acquire() as connection:
            yield connection

    async def close(self) -> None:
        if self.pool is not None:
            await self.pool.close()
            self.pool = None
