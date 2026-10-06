import asyncio
import random
from dataclasses import dataclass
from typing import Optional

from utils.db_client import DBClient

# How much each level of taste counts toward a candidate song's group score.
WEIGHTS: dict[str, float] = {"song": 0.5, "artist": 0.3, "genre": 0.2}
SEED_LIMIT = 50  # top liked songs/artists/genres used to find candidates
CANDIDATE_LIMIT = 500
TOP_K = 10  # pick randomly (weighted) among this many best candidates
RECENT_MINUTES = 5  # don't repeat a song played in the channel this recently
DISLIKE_THRESHOLD = 0.35  # never pick a song the group scores below this

KINDS: dict[str, str] = {
    "song": "song_user_likes",
    "artist": "artist_user_likes",
    "genre": "genre_user_likes",
}


@dataclass(frozen=True)
class Candidate:
    song_id: int
    title: str
    artist: str
    artist_id: int
    genre_ids: list[int]


@dataclass(frozen=True)
class Pick:
    song_id: int
    title: str
    artist: str
    score: float


class Curator(DBClient):
    """Picks what a voice channel should hear next from the combined taste of
    everyone in it. Stateless: membership comes from Discord and scores from
    Postgres on every call, so any process can curate any channel."""

    async def group_scores(self, member_ids: list[int]) -> dict[str, dict[int, float]]:
        """Average song/artist/genre scores across the members (missing = neutral)."""
        members = sorted(set(member_ids))

        async def fetch(table: str) -> dict[int, float]:
            rows = await self.db.fetch(
                self.build_group_scores_query(table), members, len(members)
            )
            return {row["item_id"]: row["score"] for row in rows}

        results = await asyncio.gather(*(fetch(table) for table in KINDS.values()))
        return dict(zip(KINDS, results))

    async def candidates(
        self,
        channel_id: int,
        scores: dict[str, dict[int, float]],
        exclude_song_ids: Optional[list[int]] = None,
    ) -> list[Candidate]:
        """Songs connected to anything the group likes, minus recent plays and
        `exclude_song_ids`. Direct song matches rank first, then artist
        matches, then genre."""
        seeds = {kind: self.top_liked(scores[kind]) for kind in KINDS}
        rows = await self.db.fetch(
            """
            SELECT s.id AS song_id, s.title, a.name AS artist, s.artist_id,
                   ARRAY(SELECT genre_id FROM artist_genres
                         WHERE artist_id = s.artist_id) AS genre_ids
            FROM songs s
            JOIN artists a ON a.id = s.artist_id
            WHERE (s.id = ANY($1::int[])
                   OR s.artist_id = ANY($2::int[])
                   OR s.artist_id IN (SELECT artist_id FROM artist_genres
                                      WHERE genre_id = ANY($3::int[])))
              AND NOT EXISTS (
                  SELECT 1 FROM plays p
                  WHERE p.channel_id = $4 AND p.song_id = s.id
                    AND p.started_at > now() - make_interval(mins => $5))
              AND NOT (s.id = ANY($7::int[]))
            ORDER BY s.id = ANY($1::int[]) DESC, s.artist_id = ANY($2::int[]) DESC
            LIMIT $6
            """,
            seeds["song"],
            seeds["artist"],
            seeds["genre"],
            channel_id,
            RECENT_MINUTES,
            CANDIDATE_LIMIT,
            exclude_song_ids or [],
        )
        return [
            Candidate(
                song_id=row["song_id"],
                title=row["title"],
                artist=row["artist"],
                artist_id=row["artist_id"],
                genre_ids=list(row["genre_ids"]),
            )
            for row in rows
        ]

    async def pick_next(
        self,
        channel_id: int,
        member_ids: list[int],
        rng: Optional[random.Random] = None,
        exclude_song_ids: Optional[list[int]] = None,
    ) -> Optional[Pick]:
        """Choose the next song for the room, or None if there isn't enough
        history yet (cold start) to pick anything the room likes.

        `exclude_song_ids` covers songs the recent-plays check can't see yet,
        e.g. the one playing right now while the next pick is prepared."""
        if not member_ids:
            return None
        scores = await self.group_scores(member_ids)
        if not any(scores.values()):
            return None
        candidates = await self.candidates(channel_id, scores, exclude_song_ids)
        return self.choose(candidates, scores, rng or random.Random())

    @classmethod
    def top_liked(cls, scores: dict[int, float]) -> list[int]:
        liked = [item for item, score in scores.items() if score > cls.NEUTRAL_SCORE]
        liked.sort(key=lambda item: scores[item], reverse=True)
        return liked[:SEED_LIMIT]

    @classmethod
    def score_candidate(
        cls, candidate: Candidate, scores: dict[str, dict[int, float]]
    ) -> float:
        neutral = cls.NEUTRAL_SCORE
        genre_scores = [scores["genre"].get(g, neutral) for g in candidate.genre_ids]
        parts = {
            "song": scores["song"].get(candidate.song_id, neutral),
            "artist": scores["artist"].get(candidate.artist_id, neutral),
            "genre": (
                sum(genre_scores) / len(genre_scores) if genre_scores else neutral
            ),
        }
        return sum(WEIGHTS[kind] * value for kind, value in parts.items())

    @classmethod
    def choose(
        cls,
        candidates: list[Candidate],
        scores: dict[str, dict[int, float]],
        rng: random.Random,
    ) -> Optional[Pick]:
        """Weighted-random pick among the TOP_K best above-neutral candidates;
        weighting by margin over neutral keeps variety without picking duds."""
        ranked = sorted(
            (
                (cls.score_candidate(c, scores), c)
                for c in candidates
                if scores["song"].get(c.song_id, cls.NEUTRAL_SCORE) >= DISLIKE_THRESHOLD
            ),
            key=lambda pair: pair[0],
            reverse=True,
        )
        top = [(s, c) for s, c in ranked[:TOP_K] if s > cls.NEUTRAL_SCORE]
        if not top:
            return None
        score, chosen = rng.choices(
            top, weights=[s - cls.NEUTRAL_SCORE for s, _ in top]
        )[0]
        return Pick(
            song_id=chosen.song_id,
            title=chosen.title,
            artist=chosen.artist,
            score=score,
        )
