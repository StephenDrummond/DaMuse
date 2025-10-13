from utils.db_client import DBClient


class Curator(DBClient):
    def __init__(self):
        super().__init__()
