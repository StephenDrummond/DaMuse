from typing import List

from utils.db_client import DBClient


class Curator(DBClient):
    channel_id = None  # key to access redis / primary identifier for the Curator object
    member_list: List[int] = []  # key to access redis / stored as discord_id

    # preferred_genres = pd.DataFrame(columns=["user", "genre", "preference"])
    # preferred_artists = pd.DataFrame(columns=["user", "artist", "preference"])
    # preferred_songs = pd.DataFrame(columns=["user", "song", "preference"])

    def __init__(self, db, channel_id, member_list):
        super().__init__(db)
        self.channel_id = channel_id
        self.member_list = member_list

    async def update(self): ...
