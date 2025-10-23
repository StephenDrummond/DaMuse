import asyncio
import json
import random
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
        tasks = [
            self.gather_data("song"),
            self.gather_data("genre"),
            self.gather_data("artist"),
        ]

        song_prefs, genre_prefs, artist_prefs = await asyncio.gather(*tasks)
        window = (
            20 if len(genre_prefs) >= 20 else len(genre_prefs)
        )  # assign the window size for a genre
        selection = random.randint(0, window - 1)  # noqa: F841 #JUST FOR NOW

    async def gather_data(self, pref_type: str):
        """this model returns averages for the preferences of all channel members"""
        rows = []

        for member in self.member_ids:
            data = await self.r.get(f"{self.channel_id}:{member}:{pref_type}")
            if not data:
                continue
            data = json.loads(data)
            rows.append(data)

        df = pd.DataFrame(rows, columns=(f"{pref_type}_id", "pref_score"))
        df = df.groupby("pref_score", as_index=False)
        return df.mean().sort_values("pref_score", ascending=False)

    async def update(self): ...
