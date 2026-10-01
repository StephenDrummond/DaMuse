from dataclasses import dataclass
from typing import Optional

from .db_client import DBClient

# Postgres NOTIFY channel workers LISTEN on to pick up new jobs immediately.
NOTIFY_CHANNEL = "audio_jobs"
MAX_ATTEMPTS = 3
# A claimed job not finished in this long is assumed dead (worker crashed)
# and becomes claimable again.
LEASE_MINUTES = 15


@dataclass(frozen=True)
class AudioJob:
    audio_key: str
    source_url: str
    attempts: int


class AudioJobs(DBClient):
    """Postgres-backed queue of songs to download, encode and upload to S3.

    One row per audio key, so a song requested by many guilds at once is only
    encoded once. Workers claim rows with FOR UPDATE SKIP LOCKED, so any
    number of them can run against the same table safely.
    """

    async def enqueue(self, audio_key: str, source_url: str) -> None:
        """Queue a song for caching. A no-op if it's already queued/running.

        A 'done' job is re-queued: the bot only enqueues after S3 said the
        file is missing, so it was deleted (e.g. by a lifecycle rule). A
        'failed' one is retried once it's a day old.
        """
        await self.db.execute(
            """
            WITH upsert AS (
                INSERT INTO audio_jobs (audio_key, source_url)
                VALUES ($1::text, $2::text)
                ON CONFLICT (audio_key) DO UPDATE
                SET status = 'pending', attempts = 0, last_error = NULL,
                    source_url = EXCLUDED.source_url, updated_at = now()
                WHERE audio_jobs.status = 'done'
                   OR (audio_jobs.status = 'failed'
                       AND audio_jobs.updated_at < now() - interval '1 day')
                RETURNING 1
            )
            SELECT pg_notify($3::text, $1::text) FROM upsert
            """,
            audio_key,
            source_url,
            NOTIFY_CHANNEL,
        )

    async def claim(self) -> Optional[AudioJob]:
        """Take the oldest available job (or a stalled one), or None."""
        row = await self.db.fetch_row(
            f"""
            UPDATE audio_jobs
            SET status = 'running', attempts = attempts + 1,
                locked_until = now() + interval '{LEASE_MINUTES} minutes',
                updated_at = now()
            WHERE audio_key = (
                SELECT audio_key FROM audio_jobs
                WHERE (status = 'pending'
                       OR (status = 'running' AND locked_until < now()))
                  AND attempts < $1
                ORDER BY created_at
                FOR UPDATE SKIP LOCKED
                LIMIT 1
            )
            RETURNING audio_key, source_url, attempts
            """,
            MAX_ATTEMPTS,
        )
        if row is None:
            return None
        return AudioJob(
            audio_key=row["audio_key"],
            source_url=row["source_url"],
            attempts=row["attempts"],
        )

    async def complete(self, audio_key: str) -> None:
        await self.db.execute(
            """
            UPDATE audio_jobs
            SET status = 'done', last_error = NULL, locked_until = NULL,
                updated_at = now()
            WHERE audio_key = $1
            """,
            audio_key,
        )

    async def fail(self, job: AudioJob, error: str, permanent: bool = False) -> None:
        """Release a failed job: back to 'pending' for another attempt, or
        'failed' once it's out of attempts (or the error can't be retried)."""
        give_up = permanent or job.attempts >= MAX_ATTEMPTS
        await self.db.execute(
            """
            UPDATE audio_jobs
            SET status = $2, last_error = $3, locked_until = NULL, updated_at = now()
            WHERE audio_key = $1
            """,
            job.audio_key,
            "failed" if give_up else "pending",
            error[:2000],
        )
