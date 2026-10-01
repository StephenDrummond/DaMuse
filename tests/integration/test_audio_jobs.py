"""The audio_jobs queue against real Postgres: upsert rules, SKIP LOCKED
claiming, leases, retries and LISTEN/NOTIFY."""

import asyncio

import pytest

from utils.audio_jobs import MAX_ATTEMPTS, NOTIFY_CHANNEL, AudioJobs


@pytest.fixture
def jobs(pg):
    return AudioJobs(pg)


async def status(pg, key):
    return await pg.fetch_row(
        "SELECT status, attempts, last_error FROM audio_jobs WHERE audio_key = $1", key
    )


@pytest.mark.asyncio
async def test_enqueue_is_idempotent(jobs, pg):
    await jobs.enqueue("youtube/a", "https://youtu.be/a")
    await jobs.enqueue("youtube/a", "https://youtu.be/a")

    assert await pg.fetch_val("SELECT count(*) FROM audio_jobs") == 1
    assert (await status(pg, "youtube/a"))["status"] == "pending"


@pytest.mark.asyncio
async def test_enqueue_notifies_only_when_queued(jobs, pg):
    received: list[str] = []

    def on_notify(*args):
        received.append(args[3])

    async with pg.connection() as listener:
        await listener.add_listener(NOTIFY_CHANNEL, on_notify)
        try:
            await jobs.enqueue("youtube/a", "u")
            await jobs.enqueue("youtube/a", "u")  # already pending: no new work
            await asyncio.sleep(0.2)
        finally:
            await listener.remove_listener(NOTIFY_CHANNEL, on_notify)

    assert received == ["youtube/a"]


@pytest.mark.asyncio
async def test_claim_takes_oldest_and_marks_running(jobs, pg):
    await jobs.enqueue("youtube/a", "ua")
    await jobs.enqueue("youtube/b", "ub")

    job = await jobs.claim()

    assert job is not None and (job.audio_key, job.attempts) == ("youtube/a", 1)
    assert (await status(pg, "youtube/a"))["status"] == "running"
    assert (await status(pg, "youtube/b"))["status"] == "pending"


@pytest.mark.asyncio
async def test_claim_empty_queue(jobs):
    assert await jobs.claim() is None


@pytest.mark.asyncio
async def test_concurrent_claims_never_share_a_job(jobs):
    for i in range(10):
        await jobs.enqueue(f"youtube/{i}", "u")

    claimed = await asyncio.gather(*(jobs.claim() for _ in range(15)))

    keys = [job.audio_key for job in claimed if job is not None]
    assert len(keys) == 10
    assert len(set(keys)) == 10  # SKIP LOCKED: no job handed out twice


@pytest.mark.asyncio
async def test_claim_skips_jobs_locked_by_another_worker(jobs, pg):
    await jobs.enqueue("youtube/a", "ua")
    await jobs.enqueue("youtube/b", "ub")

    async with pg.transaction() as other_worker:
        # another worker is mid-claim on the oldest job
        await other_worker.execute(
            "SELECT 1 FROM audio_jobs WHERE audio_key = 'youtube/a' FOR UPDATE"
        )
        # without SKIP LOCKED this would block until the other one commits
        job = await asyncio.wait_for(jobs.claim(), timeout=5)

    assert job is not None and job.audio_key == "youtube/b"


@pytest.mark.asyncio
async def test_running_job_is_not_reclaimed_until_lease_expires(jobs, pg):
    await jobs.enqueue("youtube/a", "u")
    assert await jobs.claim() is not None

    assert await jobs.claim() is None  # leased

    await pg.execute("UPDATE audio_jobs SET locked_until = now() - interval '1 second'")
    stalled = await jobs.claim()
    assert stalled is not None and stalled.attempts == 2


@pytest.mark.asyncio
async def test_complete(jobs, pg):
    await jobs.enqueue("youtube/a", "u")
    job = await jobs.claim()
    assert job is not None

    await jobs.complete(job.audio_key)

    assert (await status(pg, "youtube/a"))["status"] == "done"
    assert await jobs.claim() is None


@pytest.mark.asyncio
async def test_retry_until_max_attempts(jobs, pg):
    await jobs.enqueue("youtube/a", "u")

    for attempt in range(1, MAX_ATTEMPTS + 1):
        job = await jobs.claim()
        assert job is not None and job.attempts == attempt
        await jobs.fail(job, f"boom {attempt}")

    row = await status(pg, "youtube/a")
    assert (row["status"], row["last_error"]) == ("failed", f"boom {MAX_ATTEMPTS}")
    assert await jobs.claim() is None


@pytest.mark.asyncio
async def test_permanent_failure_is_not_retried(jobs, pg):
    await jobs.enqueue("youtube/a", "u")
    job = await jobs.claim()
    assert job is not None

    await jobs.fail(job, "too long", permanent=True)

    assert (await status(pg, "youtube/a"))["status"] == "failed"
    assert await jobs.claim() is None


@pytest.mark.asyncio
async def test_enqueue_requeues_done_job(jobs, pg):
    # the bot only enqueues after an S3 miss, so a 'done' job lost its file
    await jobs.enqueue("youtube/a", "u")
    job = await jobs.claim()
    assert job is not None
    await jobs.complete(job.audio_key)

    await jobs.enqueue("youtube/a", "u")

    row = await status(pg, "youtube/a")
    assert (row["status"], row["attempts"]) == ("pending", 0)


@pytest.mark.asyncio
async def test_failed_job_requeued_only_after_a_day(jobs, pg):
    await jobs.enqueue("youtube/a", "u")
    job = await jobs.claim()
    assert job is not None
    await jobs.fail(job, "nope", permanent=True)

    await jobs.enqueue("youtube/a", "u")
    assert (await status(pg, "youtube/a"))["status"] == "failed"

    await pg.execute("UPDATE audio_jobs SET updated_at = now() - interval '2 days'")
    await jobs.enqueue("youtube/a", "u")
    assert (await status(pg, "youtube/a"))["status"] == "pending"


@pytest.mark.asyncio
async def test_enqueue_leaves_running_job_alone(jobs, pg):
    await jobs.enqueue("youtube/a", "u")
    assert await jobs.claim() is not None

    await jobs.enqueue("youtube/a", "u")

    row = await status(pg, "youtube/a")
    assert (row["status"], row["attempts"]) == ("running", 1)
