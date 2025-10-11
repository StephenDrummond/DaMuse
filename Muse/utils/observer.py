from .db_client import DBClient


class Observer(DBClient):
    def __init__(self):
        super().__init__()
