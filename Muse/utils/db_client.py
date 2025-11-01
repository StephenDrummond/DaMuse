import asyncio

import asyncpg
from asyncpg import Record
from datetime import datetime

from db.db import Database  # type: ignore


class DBClient(object):
    def __init__(self, db):
        self.db: Database = db

    async def get_user_id(self, discord_id: int) -> int | None:
        query = """
            SELECT user_id
            FROM users
            WHERE discord_id = ($1)
        """
        return await self.db.fetch_val(query, discord_id)

    async def insert_if_not_exists(
        self, table: str, columns: list[str], *values
    ) -> None:
        """Insert a row; skip if key already exists."""
        col_str = ", ".join(columns)
        val_str = ", ".join(f"${i + 1}" for i in range(len(values)))
        query = f"""
            INSERT INTO {table} ({col_str})
            VALUES ({val_str})
            ON CONFLICT ({columns[0]}) DO NOTHING
        """
        await self.db.execute(query, *values)

    async def get_target_id(
        self, table_name: str, lookup_column: str, value: str
    ) -> int:
        """Fetch the ID for a target value in a table."""
        query = f"SELECT id FROM {table_name} WHERE {lookup_column} = $1"
        target_id = await self.db.fetch_val(query, value)
        if target_id is None:
            raise ValueError(f"No ID found for {value} in {table_name}")
        return target_id

    async def upsert_all_preferences(
        self, table: str, user: int, rows: dict[int, float]
    ):
        """Insert or update multiple records efficiently using executemany()."""
        item_column = table.split("_", 1)[0] + "_id"
        key_columns = ["user_id", item_column]
        update_columns = ["preference_score", "liked_at"]

        try:
            # Convert dict into list of tuples for executemany
            values = [
                (user, item_id, pref_score, datetime.now())
                for item_id, pref_score in rows.items()
            ]

            # Build query using first row just to get placeholders
            query = self.build_upsert_query(
                table, key_columns, update_columns, values[0]
            )

            await self.db.batch_insert(query, values)

        except Exception as e:
            print(f"Error bulk upserting {table} with {len(rows)} rows: {e}")

    async def upsert_preference(self, table: str, *values):
        """Insert or update a record. Binds preference between [0,1]."""
        key_columns = ", ".join(["user_id", table.split("_", 1)[0]])
        update_columns = ["liked", "liked_at", "preference_score"]
        try:
            query = self.build_upsert_query(table, key_columns, update_columns, values)
            await self.db.execute(query, *values)
        except Exception as e:
            print(f"Error upserting {table} with values {values}: {e}")

    async def fetch_preferences(
        self, discord_id: int, table: str
    ) -> list[Record] | None:
        query = self.build_pref_table_query(table)

        try:
            return await self.db.fetch(query, discord_id)
        except asyncpg.PostgresError as e:
            print(e)
            return None

    @staticmethod
    def build_pref_table_query(pref_table: str) -> str:
        """Builds query for fetching a user’s preferences from given table name"""
        type_table = pref_table.split("_", 1)[0] + "s"  # ex song_user_likes -> songs
        type_word = pref_table.split("_", 1)[0]  # ex song_user_likes -> song

        query = f"""
            (SELECT
            tt.id AS {type_word}_id,
            tt.name AS {type_word}_name,
            pt.preference_score AS preference_score
            FROM users u
            JOIN {pref_table} pt ON u.discord_id = pt.user_id
            JOIN {type_table} tt ON pt.{type_word}_id= tt.id
            WHERE u.discord_id = ($1)
            and pt.preference_score > 0.7
            order by pt.preference_score desc
            limit 200
            )
            union all
            (SELECT
            tt.id AS {type_word}_id,
            tt.name AS {type_word}_name,
            pt.preference_score AS preference_score
            FROM users u
            JOIN {pref_table} pt ON u.discord_id = pt.user_id
            JOIN {type_table} tt ON pt.{type_word}_id = tt.id
            WHERE u.discord_id = ($1)
            and pt.preference_score < 0.3
            order by pt.preference_score asc
            limit 200
            );"""
        return query

    @staticmethod
    def build_upsert_query(
        table: str,
        key_columns: list[str],
        update_columns: list[str],
        values: tuple[int, int, float],
    ) -> str:
        key_str = ", ".join(key_columns)

        update_str = ", ".join(
            f"{col} = "
            + (
                f"GREATEST(LEAST(EXCLUDED.{col}, 1.0), 0.0)"
                if col == "preference_score"
                else f"EXCLUDED.{col}"
            )
            for col in update_columns
        )

        placeholders = ", ".join(f"${i + 1}" for i in range(len(values)))

        return f"""
            INSERT INTO {table} ({', '.join(key_columns + update_columns)})
            VALUES ({placeholders})
            ON CONFLICT ({key_str}) DO UPDATE
            SET {update_str};
        """


async def main(
    table="song_user_likes", user=283796442437517313, rows={1027: 0.9, 4965: 0.3}
):
    db = Database()
    await db.init_pool()
    dbc = DBClient(db)

    await dbc.upsert_all_preferences(table, user, rows)


asyncio.run(main())
