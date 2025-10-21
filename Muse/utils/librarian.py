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


if __name__ == "__main__":
    from api.spotify import get_spotify_info
    import asyncio

    async def main():
        librarian = Librarian()
        await librarian.create_db()

        song = "rockafeller skank"

        info = await get_spotify_info(song)

        class FakeMember:
            id = 1234567890

        member = FakeMember()

        await librarian.add_artist_to_db(info["artists"][0])
        artist_id: int = await librarian.db.fetch_val(
            "SELECT id FROM artists WHERE name = $1", info["artists"][0]
        )
        title = info["name"]

        await librarian.add_songs_to_db(title, artist_id)

        await librarian.add_member_to_db(123456)
        await librarian.add_member_to_db(234567)

        for genre in info["genres"]:
            await librarian.add_genre_to_db(genre)

    asyncio.run(main())
