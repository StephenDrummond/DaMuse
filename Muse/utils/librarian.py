from .db_client import DBClient


class Librarian(DBClient):
    def __init__(self, db):
        super().__init__(db)

    async def add_member_to_db(self, member_id: int):
        await self.insert_if_not_exists("users", ["discord_id"], member_id)

    async def add_artist_to_db(self, artist_name: str):
        await self.insert_if_not_exists("artists", ["name"], artist_name)

    async def add_songs_to_db(self, title: str, artist_id: int):
        await self.insert_if_not_exists(
            "songs", ["title", "artist_id"], title, artist_id
        )

    async def add_genre_to_db(self, name: str):
        await self.insert_if_not_exists("genres", ["name"], name)
