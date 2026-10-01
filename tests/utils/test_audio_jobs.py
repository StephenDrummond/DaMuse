import pytest

from utils.audio_jobs import MAX_ATTEMPTS, NOTIFY_CHANNEL, AudioJob, AudioJobs


@pytest.mark.asyncio
async def test_enqueue_upserts_and_notifies(db):
    await AudioJobs(db).enqueue("youtube/abc", "https://youtu.be/abc")

    query, *args = db.execute.await_args.args
    assert "ON CONFLICT (audio_key) DO UPDATE" in query
    assert "pg_notify" in query
    assert args == ["youtube/abc", "https://youtu.be/abc", NOTIFY_CHANNEL]


@pytest.mark.asyncio
async def test_claim_returns_job(db):
    db.fetch_row.return_value = {
        "audio_key": "youtube/abc",
        "source_url": "u",
        "attempts": 1,
    }

    job = await AudioJobs(db).claim()

    assert job == AudioJob(audio_key="youtube/abc", source_url="u", attempts=1)
    query, max_attempts = db.fetch_row.await_args.args
    assert "FOR UPDATE SKIP LOCKED" in query
    assert max_attempts == MAX_ATTEMPTS


@pytest.mark.asyncio
async def test_claim_empty_queue(db):
    db.fetch_row.return_value = None

    assert await AudioJobs(db).claim() is None


@pytest.mark.asyncio
async def test_complete(db):
    await AudioJobs(db).complete("youtube/abc")

    query, key = db.execute.await_args.args
    assert "status = 'done'" in query
    assert key == "youtube/abc"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "attempts, permanent, expected_status",
    [
        (1, False, "pending"),  # retry
        (MAX_ATTEMPTS, False, "failed"),  # out of attempts
        (1, True, "failed"),  # can never succeed
    ],
)
async def test_fail(db, attempts, permanent, expected_status):
    job = AudioJob(audio_key="youtube/abc", source_url="u", attempts=attempts)

    await AudioJobs(db).fail(job, "boom" * 1000, permanent=permanent)

    _, key, status, error = db.execute.await_args.args
    assert (key, status) == ("youtube/abc", expected_status)
    assert len(error) == 2000  # truncated
