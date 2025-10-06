import math
import os
from datetime import datetime

import psycopg2
from dotenv import load_dotenv


class Profiler(object):
    def __init__(self, ctx):
        self.ctx = ctx

    @staticmethod
    def boost_preference(preference_score, alpha = 0.2):
        preference_score += alpha

        date = datetime.today().date()

        return {
            preference_score: preference_score,
            date: date
        }

    @staticmethod
    def forget_preference(preference_score, last_updated, _lambda=0.05):
        delta = (datetime.today().date() - last_updated).days
        return preference_score * math.exp(-delta * preference_score)

load_dotenv()
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASS")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")

try:
    conn = psycopg2.connect(database=DB_NAME, user=DB_USER, password=DB_PASSWORD, host=DB_HOST, port=DB_PORT)
    print("Connected to PostgreSQL")
    cursor = conn.cursor()
except Exception as ex:
    print(ex)
    print("database not connected")