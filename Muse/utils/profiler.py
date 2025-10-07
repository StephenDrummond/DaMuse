import math
from datetime import datetime


class Profiler(object):
    @staticmethod
    def boost_preference(preference_score, alpha=0.2):
        preference_score += alpha

        date = datetime.today().date()

        return {
            preference_score: preference_score,
            date: date
        }

    @staticmethod
    def forget_preference(preference_score, last_updated, _lambda=0.05):
        delta = (datetime.today().date() - last_updated).days
        return preference_score * math.exp(-delta * _lambda)
