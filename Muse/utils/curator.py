from utils.db_client import DBClient


class Curator(DBClient):
    def __init__(self, db):
        super().__init__(db)
