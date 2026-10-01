import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import worker
from utils.audio_jobs import AudioJob
from utils.encoder import PermanentEncodeError

JOB = AudioJob(audio_key="youtube/abc", source_url="u", attempts=1)


@pytest.fixture
def jobs():
    return AsyncMock()


@pytest.fixture
def store():
    store = MagicMock()
    store.bucket = "bucket"
    return store


@pytest.mark.asyncio
async def test_process_success(jobs, store):
    with patch.object(worker, "encode_and_upload", return_value="key"):
        await worker.process(JOB, jobs, store)

    jobs.complete.assert_awaited_once_with("youtube/abc")
    jobs.fail.assert_not_awaited()


@pytest.mark.asyncio
async def test_process_permanent_failure(jobs, store):
    with patch.object(
        worker, "encode_and_upload", side_effect=PermanentEncodeError("too long")
    ):
        await worker.process(JOB, jobs, store)

    jobs.fail.assert_awaited_once_with(JOB, "too long", permanent=True)


@pytest.mark.asyncio
async def test_process_retryable_failure(jobs, store):
    with patch.object(worker, "encode_and_upload", side_effect=OSError("network")):
        await worker.process(JOB, jobs, store)

    jobs.fail.assert_awaited_once()
    assert jobs.fail.await_args.kwargs == {}  # not permanent
    jobs.complete.assert_not_awaited()


def test_encode_and_upload_cleans_up(store, tmp_path):
    encoded = MagicMock(path="p", metadata={"title": "t"})
    with (
        patch.object(worker, "fetch_and_encode", return_value=encoded) as fetch,
        patch.object(worker.tempfile, "TemporaryDirectory") as tempdir,
    ):
        tempdir.return_value.__enter__.return_value = str(tmp_path)
        worker.encode_and_upload(JOB, store)

    fetch.assert_called_once_with("u", str(tmp_path))
    store.upload.assert_called_once_with("p", "youtube/abc", {"title": "t"})
    tempdir.return_value.__exit__.assert_called_once()


@pytest.mark.asyncio
async def test_run_slot_drains_queue_then_waits(jobs, store):
    jobs.claim.side_effect = [JOB, None, asyncio.CancelledError()]
    wake = asyncio.Event()
    with (
        patch.object(worker, "process", new_callable=AsyncMock) as process,
        patch.object(worker, "POLL_SECONDS", 0),
    ):
        with pytest.raises(asyncio.CancelledError):
            await worker.run_slot(jobs, store, wake)

    process.assert_awaited_once_with(JOB, jobs, store)
    assert jobs.claim.await_count == 3
