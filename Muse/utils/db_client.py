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

    async def upsert_preferences(
        self, table: str, key_columns: list[str], update_columns: list[str], *values
    ):
        """

        Behavior:
        - If the record does NOT exist → inserts it with the given values.
        - If the record already exists → updates it.
        - `preference_score` is incremented by the new value (`+ EXCLUDED.preference_score`)
        - All other columns are replaced by their new values.

        Parameters:
            table (str): Name of the target database table.
            key_columns (list[str]): Columns for keys to the table
            update_columns (list[str]): Columns to update when a conflict occurs.
            *values: Actual values to insert, matching the order of (key_columns + update_columns).
        """
        key_str = ", ".join(key_columns)

        # What the function will be upserting with respect to preference score being base + alpha or existing + alpha
        update_str = ", ".join(
            f"{col} = "
            + (
                f"GREATEST(LEAST({table}.{col} + EXCLUDED.{col}, 1.0), 0.0)"  # does not allow prefscore to be <0 or >1
                if col == "preference_score"
                else f"EXCLUDED.{col}"
            )
            for col in update_columns
        )

        # ( $1, $2, $3...) values for postgres placeholders
        placeholders = ", ".join(f"${i+1}" for i in range(len(values)))
        query = f"""
            INSERT INTO {table} ({', '.join(key_columns + update_columns)})
            VALUES ({placeholders})
            ON CONFLICT ({key_str}) DO UPDATE
            SET {update_str}
        """
        print(query)
        await self.db.execute(query, *values)
