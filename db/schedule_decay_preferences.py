import asyncio

from config import Settings
from db.db import Database

# Each night, every score not touched in the last day moves 5% of the way back
# toward neutral (0.5), i.e. score' = 0.5 + (score - 0.5) * e^-0.05. Because the
# factor is constant per day, an untouched score's distance from neutral decays
# as e^(-0.05 * days idle): a ~14-day half-life. Decaying toward 0.5 rather
# than 0 means an old like fades to "no opinion", not into a dislike.
DECAY_RATE = 0.05

DECAY_FUNCTION = f"""
CREATE OR REPLACE FUNCTION decay_preferences()
RETURNS void AS $$
BEGIN
    UPDATE song_user_likes
    SET preference_score = 0.5 + (preference_score - 0.5) * EXP(-{DECAY_RATE})
    WHERE liked_at < now() - interval '1 day';

    UPDATE genre_user_likes
    SET preference_score = 0.5 + (preference_score - 0.5) * EXP(-{DECAY_RATE})
    WHERE liked_at < now() - interval '1 day';

    UPDATE artist_user_likes
    SET preference_score = 0.5 + (preference_score - 0.5) * EXP(-{DECAY_RATE})
    WHERE liked_at < now() - interval '1 day';
END;
$$ LANGUAGE plpgsql;
"""

# pg_cron upserts by job name, so re-running this script just updates the job.
SCHEDULE_JOB = """
SELECT cron.schedule(
    'nightly_preference_decay',
    '0 4 * * *',
    $$SELECT decay_preferences();$$
);
"""


async def main():
    """One-off: install/refresh the nightly decay job (requires pg_cron)."""
    db = Database(Settings.from_env().database)  # same connection as the bot
    await db.init_pool()
    try:
        await db.execute(DECAY_FUNCTION)
        await db.execute(SCHEDULE_JOB)
        print(await db.fetch("SELECT jobid, jobname, schedule FROM cron.job;"))
    finally:
        await db.close()


if __name__ == "__main__":
    asyncio.run(main())
