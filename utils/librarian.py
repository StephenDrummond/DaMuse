from db.db import Database
from .db_client import DBClient


class Librarian(DBClient):
    def __init__(self, db: Database):
        super().__init__(db)

    async def add_member_to_db(self, member_id: int, member_name: str):
        if type(member_id) is not int:
            raise TypeError("member_id must be an int")

        await self.insert_if_not_exists(
            "users", ["discord_id", "username"], member_id, member_name
        )

    async def add_artist_to_db(self, artist_name: str):
        if type(artist_name) is not str:
            raise TypeError
        await self.insert_if_not_exists("artists", ["name"], artist_name)

    async def add_songs_to_db(self, title: str, artist_id: int):
        if type(artist_id) is not int or type(title) is not str:
            raise TypeError
        await self.insert_if_not_exists(
            "songs",
            ["title", "artist_id"],
            title,
            artist_id,
            conflict_columns=["title", "artist_id"],
        )

    async def add_genre_to_db(self, name: str):
        if type(name) is not str:
            raise TypeError
        await self.insert_if_not_exists("genres", ["name"], name)
