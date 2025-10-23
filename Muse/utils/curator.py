import json
from typing import List

import pandas as pd
from redis import Redis

from utils.db_client import DBClient


class Curator(DBClient):
    channel_id: int  # key to access redis / primary identifier for the Curator object
    member_ids: List[int]  # list of all members in the channel
    r: Redis

    def __init__(self, db, channel_id: int, member_list: List[int], r: Redis):
        super().__init__(db)
        self.channel_id = channel_id
        self.member_ids = member_list
        self.r = r

    async def curate(self):
        song_prefs = self.gather_data('song')
        genre_prefs = self.gather_data('genre')
        artist_prefs = self.gather_data('artist')

    async def gather_data(self, pref_type: str):
        rows = []

        for member in self.member_ids:
            data = await self.r.get(f"{self.channel_id}:{member}:{pref_type}")
            if not data: continue
            data = json.loads(data)
            rows.append(data)

        return pd.DataFrame(rows, columns=(f"{pref_type}_id", "pref_score"))

    async def update(self):
        ...
