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
