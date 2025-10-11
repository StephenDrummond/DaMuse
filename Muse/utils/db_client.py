from db.db import Database


class DBClient(object):
    def __init__(self):
        self.db = Database()

    async def create_db(self):
        await self.db.init_pool()

    async def insert_if_not_exists(
        self, table: str, columns: list[str], *values
    ) -> None:
        """
        Generic helper to insert a row into a table with ON CONFLICT DO NOTHING.

        Args:
            table: Table name
            columns: List of column names
            *values: Values to insert in order
        """
        col_str = ", ".join(columns)
        val_str = ", ".join(f"${i+1}" for i in range(len(values)))
        query = f"""
            INSERT INTO {table} ({col_str})
            VALUES ({val_str})
            ON CONFLICT ({columns[0]}) DO NOTHING
        """
        await self.db.execute(query, *values)

    async def upsert(
        self, table: str, key_columns: list[str], update_columns: list[str], *values
    ):
        """
        Generic UPSERT (insert or update) helper.
        """
        key_str = ", ".join(key_columns)
        update_str = ", ".join(f"{col} = EXCLUDED.{col}" for col in update_columns)
        placeholders = ", ".join(f"${i+1}" for i in range(len(values)))
        query = f"""
            INSERT INTO {table} ({', '.join(key_columns + update_columns)})
            VALUES ({placeholders})
            ON CONFLICT ({key_str}) DO UPDATE
            SET {update_str}
        """
        await self.db.execute(query, *values)
