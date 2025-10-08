from db.db import Database


class Librarian(object):
    def __init__(self):
        self.db: Database = Database()

    async def add_member_to_db(self, member_id: int) -> None:
        await self.db.execute("""
        INSERT INTO users (discord_id)
        VALUES ($1)
        ON CONFLICT (discord_id) DO NOTHING
        """, member_id)

    async def add_artist_to_db(self, artist_name: str) -> None:
        await self.db.execute("""
        INSERT INTO artists (name)
        VALUES ($1)
        ON CONFLICT (name) DO NOTHING
        """, artist_name)

    async def add_songs_to_db(self, title: str, artist_id) -> None:
        await self.db.execute("""
        INSERT INTO songs (title, artist_id)
        VALUES ($1, $2)
        ON CONFLICT (title) DO NOTHING
        """, title, artist_id)

    async def add_genre_to_db(self, name: str) -> None:
        await self.db.execute("""
        INSERT INTO genres (name)
        VALUES ($1)
        ON CONFLICT (name) DO NOTHING""", name)
