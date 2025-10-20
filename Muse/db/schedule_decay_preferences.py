import asyncio
import os

import asyncpg
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASS")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")


async def run_sql_query(query, fetch=False):
    try:
        connection = await asyncpg.connect(
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT,
        )
        print("Database connection created")

        if fetch:
            rows = await connection.fetch(query)
            await connection.close()
            return rows
        else:
            await connection.execute(query)
            await connection.close()

    except Exception as e:
        print(e)


async def main():
    # 1 — Create decay function
    await run_sql_query(
        """
CREATE OR REPLACE FUNCTION decay_preferences()
RETURNS void AS $$
BEGIN
    UPDATE song_user_likes
    SET preference_score = preference_score * EXP(-0.05 * (CURRENT_DATE - liked_at::date))
    WHERE liked_at < CURRENT_DATE;

    UPDATE genre_user_likes
    SET preference_score = preference_score * EXP(-0.05 * (CURRENT_DATE - liked_at::date))
    WHERE liked_at < CURRENT_DATE;

    UPDATE artist_user_likes
    SET preference_score = preference_score * EXP(-0.05 * (CURRENT_DATE - liked_at::date))
    WHERE liked_at < CURRENT_DATE;
END;
$$ LANGUAGE plpgsql;
    """,  # noqa: E501
        fetch=False,
    )

    # 2 — Schedule with pg_cron (Every night at 4 AM decay_preferences() runs)
    await run_sql_query(
        """
SELECT cron.schedule(
    'nightly_preference_decay',
    '0 4 * * *',
    $$SELECT decay_preferences();$$
);
    """,
        fetch=False,
    )

    # 3 — List jobs to check that it worked
    cron_jobs = await run_sql_query(
        """
SELECT * FROM cron.job;
    """,
        fetch=True,
    )

    print(cron_jobs)


asyncio.run(main())
