from .db_client import DBClient


class Observer(DBClient):
    def __init__(self, db):
        super().__init__(db)