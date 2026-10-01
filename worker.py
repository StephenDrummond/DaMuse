"""Audio cache worker: turns queued audio_jobs into Ogg Opus files in S3.

Run alongside the bot (any number of copies, on any machine with ffmpeg and
access to the DB + bucket):

    python worker.py

Each copy runs AUDIO_WORKER_CONCURRENCY jobs at once. New jobs arrive via
Postgres LISTEN/NOTIFY, with a periodic poll as a fallback (e.g. if the
listening connection drops during an Aurora failover).
"""

import asyncio
import logging
import os
import sys
import tempfile

from api.audio_store import AudioStore
from db.db import Database
from utils.audio_jobs import NOTIFY_CHANNEL, AudioJob, AudioJobs
from utils.encoder import PermanentEncodeError, fetch_and_encode

CONCURRENCY = int(os.getenv("AUDIO_WORKER_CONCURRENCY", "2"))
POLL_SECONDS = 30

logger = logging.getLogger("worker")


def encode_and_upload(job: AudioJob, store: AudioStore) -> str:
    """Blocking: download, encode and upload one job; returns the S3 key."""
    with tempfile.TemporaryDirectory(prefix="damuse-") as workdir:
        encoded = fetch_and_encode(job.source_url, workdir)
        return store.upload(encoded.path, job.audio_key, encoded.metadata)


async def process(job: AudioJob, jobs: AudioJobs, store: AudioStore) -> None:
    logger.info("Caching %s (attempt %d)", job.audio_key, job.attempts)
    try:
        key = await asyncio.to_thread(encode_and_upload, job, store)
    except PermanentEncodeError as error:
        logger.warning("Not caching %s: %s", job.audio_key, error)
        await jobs.fail(job, str(error), permanent=True)
    except Exception as error:
        logger.exception("Caching %s failed", job.audio_key)
        await jobs.fail(job, repr(error))
    else:
        await jobs.complete(job.audio_key)
        logger.info("Cached %s at s3://%s/%s", job.audio_key, store.bucket, key)


async def run_slot(jobs: AudioJobs, store: AudioStore, wake: asyncio.Event) -> None:
    """One concurrent job slot: drain the queue, then sleep until notified."""
    while True:
        wake.clear()
        job = await jobs.claim()
        if job is not None:
            await process(job, jobs, store)
            continue
        try:
            await asyncio.wait_for(wake.wait(), POLL_SECONDS)
        except asyncio.TimeoutError:
            pass


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    store = AudioStore.from_env()
    if store is None:
        sys.exit("AUDIO_BUCKET must be set for the worker")

    db = Database()
    await db.init_pool()
    if db.pool is None:
        sys.exit("Couldn't connect to the database")
    jobs = AudioJobs(db)

    wake = asyncio.Event()
    listener = await db.pool.acquire()
    await listener.add_listener(NOTIFY_CHANNEL, lambda *_: wake.set())
    logger.info("Worker started with %d slots", CONCURRENCY)
    try:
        await asyncio.gather(*(run_slot(jobs, store, wake) for _ in range(CONCURRENCY)))
    finally:
        await db.pool.release(listener)
        await db.close()


if __name__ == "__main__":
    asyncio.run(main())
