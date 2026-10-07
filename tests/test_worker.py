import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import worker
from audio.audio_jobs import AudioJob
from audio.encoder import PermanentEncodeError

JOB = AudioJob(audio_key="youtube/abc", source_url="u", attempts=1)


@pytest.fixture
def jobs():
    return AsyncMock()


@pytest.fixture
def store():
    store = MagicMock()
    store.bucket = "bucket"
    return store


@pytest.fixture
def encoder():
    return MagicMock()


@pytest.fixture
def make_worker(jobs, store, encoder):
    return lambda: worker.Worker(jobs, store, encoder)


@pytest.mark.asyncio
async def test_process_success(jobs, make_worker):
    w = make_worker()
    with patch.object(w, "encode_and_upload", return_value="key"):
        await w.process(JOB)

    jobs.complete.assert_awaited_once_with("youtube/abc")
    jobs.fail.assert_not_awaited()


@pytest.mark.asyncio
async def test_process_permanent_failure(jobs, make_worker):
    w = make_worker()
    with patch.object(
        w, "encode_and_upload", side_effect=PermanentEncodeError("too long")
    ):
        await w.process(JOB)

    jobs.fail.assert_awaited_once_with(JOB, "too long", permanent=True)


@pytest.mark.asyncio
async def test_process_retryable_failure(jobs, make_worker):
    w = make_worker()
    with patch.object(w, "encode_and_upload", side_effect=OSError("network")):
        await w.process(JOB)

    jobs.fail.assert_awaited_once()
    assert jobs.fail.await_args.kwargs == {}  # not permanent
    jobs.complete.assert_not_awaited()


def test_encode_and_upload_cleans_up(store, encoder, make_worker, tmp_path):
    encoder.fetch_and_encode.return_value = MagicMock(path="p", metadata={"title": "t"})
    with patch.object(worker.tempfile, "TemporaryDirectory") as tempdir:
        tempdir.return_value.__enter__.return_value = str(tmp_path)
        make_worker().encode_and_upload(JOB)

    encoder.fetch_and_encode.assert_called_once_with("u", str(tmp_path))
    store.upload.assert_called_once_with("p", "youtube/abc", {"title": "t"})
    tempdir.return_value.__exit__.assert_called_once()


@pytest.mark.asyncio
async def test_run_slot_drains_queue_then_waits(jobs, make_worker):
    jobs.claim.side_effect = [JOB, None, asyncio.CancelledError()]
    w = make_worker()
    with (
        patch.object(w, "process", new_callable=AsyncMock) as process,
        patch.object(worker, "POLL_SECONDS", 0),
    ):
        with pytest.raises(asyncio.CancelledError):
            await w.run_slot(asyncio.Event())

    process.assert_awaited_once_with(JOB)
    assert jobs.claim.await_count == 3
