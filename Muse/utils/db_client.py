import asyncpg
from asyncpg import Record

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

    async def safe_upsert_preference(
        self,
        table_name: str,
        key_columns: list[str],
        update_columns: list[str],
        *values,
    ):
        """Wraps upsert_preference with error handling."""
        try:
            await self.upsert_preference(
                table_name, key_columns, update_columns, *values
            )
        except Exception as e:
            print(f"Error upserting {table_name} with values {values}: {e}")

    async def upsert_preference(
        self, table: str, key_columns: list[str], update_columns: list[str], *values
    ):
        """Insert or update a record. Increments preference_score within [0,1]."""
        key_str = ", ".join(key_columns)
        update_str = ", ".join(
            f"{col} = "
            + (
                f"GREATEST(LEAST({table}.{col} + EXCLUDED.{col}, 1.0), 0.0)"
                if col == "preference_score"
                else f"EXCLUDED.{col}"
            )
            for col in update_columns
        )
        placeholders = ", ".join(f"${i + 1}" for i in range(len(values)))
        query = f"""
            INSERT INTO {table} ({', '.join(key_columns + update_columns)})
            VALUES ({placeholders})
            ON CONFLICT ({key_str}) DO UPDATE
            SET {update_str}
        """
        await self.db.execute(query, *values)

    async def fetch_preferences(
        self, discord_id: int, table: str
    ) -> list[Record] | None:
        query = self.pref_table_query_builder(table, discord_id)

        try:
            return await self.db.fetch_val(query, discord_id)
        except asyncpg.PostgresError as e:
            print(e)
            return None

    @staticmethod
    def pref_table_query_builder(pref_table: str, discord_id: int) -> str:
        """Builds query for fetching a user’s preferences from given table name"""
        type_table = pref_table.split("_", 1)[0] + "s"
        type_word = pref_table.split("_", 1)[0]

        query = f"""
            (SELECT
            tt.id AS {type_word}_id,
            tt.name AS {type_word}_name,
            pt.preference_score AS preference_score
            FROM users u
            JOIN {pref_table} pt ON u.id = pt.user_id
            JOIN {type_table} tt ON pt.{type_word}_id= tt.id
            WHERE u.discord_id = {discord_id}
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
            JOIN {pref_table} pt ON u.id = pt.user_id
            JOIN {type_table} tt ON pt.{type_word}_id = tt.id
            WHERE u.discord_id = {discord_id}
            and pt.preference_score < 0.3
            order by pt.preference_score asc
            limit 200
            );"""
        return query
