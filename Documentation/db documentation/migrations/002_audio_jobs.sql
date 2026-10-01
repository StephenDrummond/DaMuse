-- 002: queue of songs to download, encode to Ogg Opus and upload to S3.
-- Consumed by worker.py (see utils/audio_jobs.py for the state machine).

BEGIN;

CREATE TABLE audio_jobs (
    -- "<extractor>/<id>", e.g. "youtube/dQw4w9WgXcQ"; also the S3 key stem
    audio_key VARCHAR PRIMARY KEY,
    source_url VARCHAR NOT NULL,
    status VARCHAR NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'running', 'done', 'failed')),
    attempts INT NOT NULL DEFAULT 0,
    last_error TEXT,
    -- lease on a 'running' job; past it, the job is considered abandoned
    locked_until TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Workers scan only claimable rows, oldest first.
CREATE INDEX audio_jobs_claimable_idx ON audio_jobs (created_at)
    WHERE status IN ('pending', 'running');

COMMIT;
