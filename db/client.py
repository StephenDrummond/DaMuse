from db.db import Database  # type: ignore


class DBClient(object):
    # Maps a preference table to the (entity table, label column, id column)
    # needed to join it back to a human-readable name.
    PREFERENCE_TABLE_MAPPING: dict[str, tuple[str, str, str]] = {
        "song_user_likes": ("songs", "title", "song_id"),
        "artist_user_likes": ("artists", "name", "artist_id"),
        "genre_user_likes": ("genres", "name", "genre_id"),
    }

    # Neutral score: an item with no history for a user counts as this.
    NEUTRAL_SCORE = 0.5

    def __init__(self, db):
        self.db: Database = db

    async def insert_if_not_exists(
        self,
        table: str,
        columns: list[str],
        *values,
        conflict_columns: list[str] | None = None,
    ) -> None:
        """Insert a row; skip if the conflict target already exists."""
        col_str = ", ".join(columns)
        val_str = ", ".join(f"${i + 1}" for i in range(len(values)))
        conflict_str = ", ".join(conflict_columns or [columns[0]])
        query = f"""
            INSERT INTO {table} ({col_str})
            VALUES ({val_str})
            ON CONFLICT ({conflict_str}) DO NOTHING
        """
        await self.db.execute(query, *values)

    @classmethod
    def build_score_update_query(cls, pref_table: str) -> str:
        """Builds the write-through scoring upsert for one preference table.

        Applied to every (user, item) pair in $1::bigint[] x $2::int[], it moves
        each score toward a target ($4, 1.0 = liked, 0.0 = disliked) by a
        learning rate ($3) -- an exponential moving average:

            score <- score + rate * (target - score)

        A pair with no row yet starts from NEUTRAL_SCORE. Both arrays must be
        de-duplicated: Postgres rejects an upsert that touches a row twice.
        """
        _, _, id_column = cls.PREFERENCE_TABLE_MAPPING[pref_table]
        neutral = cls.NEUTRAL_SCORE

        return f"""
            INSERT INTO {pref_table} AS t
                (user_id, {id_column}, preference_score, liked, liked_at)
            SELECT u, i, {neutral} + $3::float8 * ($4::float8 - {neutral}),
                   $4::float8 >= {neutral}, now()
            FROM unnest($1::bigint[]) AS u
            CROSS JOIN unnest($2::int[]) AS i
            ON CONFLICT (user_id, {id_column}) DO UPDATE
            SET preference_score = GREATEST(LEAST(
                    t.preference_score
                    + $3::float8 * ($4::float8 - t.preference_score),
                    1.0), 0.0),
                liked = EXCLUDED.liked,
                liked_at = EXCLUDED.liked_at;
        """
