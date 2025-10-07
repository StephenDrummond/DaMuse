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


async def run_sql_query(query):
    try:
        connection = await asyncpg.connect(
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )
        print("Database connection created")

        rows = await connection.fetch(query)  # <-- Await fetch for SELECT queries
        await connection.close()  # <-- Close connection after done
        return rows

    except Exception as e:
        print(e)


async def main():
    info = await run_sql_query("""
        SELECT *
        FROM users;
    """)
    print(info)


asyncio.run(main())
