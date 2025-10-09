from db.db import Database


class Librarian(object):
    def __init__(self):
        self.db: Database = Database()

    async def create_db(self):
        await self.db.init_pool()

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


if __name__ == "__main__":
    import spotify
    import asyncio


    async def main():
        librarian = Librarian()
        await librarian.create_db()

        song = "money pink floyd"

        info = spotify.get_spotify_info(song)

        class FakeMember:
            id = 1234567890

        member = FakeMember()

        await librarian.add_artist_to_db(info["artists"][0])
        artist_id: int = await librarian.db.fetch_val("SELECT id FROM artists WHERE name = $1", info["artists"][0])
        title = info["name"]

        await librarian.add_songs_to_db(title, artist_id)

        await librarian.add_member_to_db(member.id)

        for genre in info["genres"]:
            await librarian.add_genre_to_db(genre)


    asyncio.run(main())
