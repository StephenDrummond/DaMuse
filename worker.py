"""Background worker for the bot. Two jobs:

- Audio cache: turns queued audio_jobs into Ogg Opus files in S3 (needs
  AUDIO_BUCKET and ffmpeg).
- Song seeding: adds known artists' Spotify top tracks to the song registry,
  so the Curator has songs to pick beyond what's been played (taste/seeder.py).

Run alongside the bot (any number of copies, on any machine with ffmpeg and
access to the DB + bucket):

    python worker.py

Each copy runs AUDIO_WORKER_CONCURRENCY jobs at once (see config.py). New jobs
arrive via Postgres LISTEN/NOTIFY, with a periodic poll as a fallback (e.g. if
the listening connection drops during an Aurora failover).
"""

import asyncio
import logging
import sys
import tempfile

from clients.audio_store import AudioStore
from clients.spotify import SpotifyClient
from config import Settings
from db.db import Database
from audio.audio_jobs import NOTIFY_CHANNEL, AudioJob, AudioJobs
from audio.encoder import Encoder, PermanentEncodeError
from taste.librarian import Librarian
from taste.seeder import Seeder

POLL_SECONDS = 30

logger = logging.getLogger("worker")


class Worker:
    def __init__(self, jobs: AudioJobs, store: AudioStore, encoder: Encoder):
        self.jobs = jobs
        self.store = store
        self.encoder = encoder

    def encode_and_upload(self, job: AudioJob) -> str:
        """Blocking: download, encode and upload one job; returns the S3 key."""
        with tempfile.TemporaryDirectory(prefix="damuse-") as workdir:
            encoded = self.encoder.fetch_and_encode(job.source_url, workdir)
            return self.store.upload(encoded.path, job.audio_key, encoded.metadata)

    async def process(self, job: AudioJob) -> None:
        logger.info("Caching %s (attempt %d)", job.audio_key, job.attempts)
        try:
            key = await asyncio.to_thread(self.encode_and_upload, job)
        except PermanentEncodeError as error:
            logger.warning("Not caching %s: %s", job.audio_key, error)
            await self.jobs.fail(job, str(error), permanent=True)
        except Exception as error:
            logger.exception("Caching %s failed", job.audio_key)
            await self.jobs.fail(job, repr(error))
        else:
            await self.jobs.complete(job.audio_key)
            logger.info(
                "Cached %s at s3://%s/%s", job.audio_key, self.store.bucket, key
            )

    async def run_slot(self, wake: asyncio.Event) -> None:
        """One concurrent job slot: drain the queue, then sleep until notified."""
        while True:
            wake.clear()
            job = await self.jobs.claim()
            if job is not None:
                await self.process(job)
                continue
            try:
                await asyncio.wait_for(wake.wait(), POLL_SECONDS)
            except asyncio.TimeoutError:
                pass


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    settings = Settings.from_env()
    if not (settings.spotify_client_id and settings.spotify_client_secret):
        sys.exit("SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET must be set")

    db = Database(settings.database)
    await db.init_pool()
    spotify = SpotifyClient(settings.spotify_client_id, settings.spotify_client_secret)
    seeder = Seeder(db, spotify, Librarian(db))
    store = AudioStore.from_settings(settings.audio, settings.aws_region)

    try:
        if store is None:
            logger.warning("Audio caching off (no AUDIO_BUCKET); seeding songs only")
            await seeder.run_forever()
            return

        worker = Worker(
            AudioJobs(db),
            store,
            Encoder.from_settings(settings.audio, settings.ffmpeg_path),
        )
        wake = asyncio.Event()
        concurrency = settings.audio.worker_concurrency
        async with db.connection() as listener:
            await listener.add_listener(NOTIFY_CHANNEL, lambda *_: wake.set())
            logger.info("Worker started: %d cache slots + song seeding", concurrency)
            await asyncio.gather(
                seeder.run_forever(),
                *(worker.run_slot(wake) for _ in range(concurrency)),
            )
    finally:
        await db.close()


if __name__ == "__main__":
    asyncio.run(main())
