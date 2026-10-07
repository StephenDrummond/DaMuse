import asyncio
import random
from dataclasses import dataclass
from typing import Optional

from db.client import DBClient

# How much each level of taste counts toward a candidate song's group score.
WEIGHTS: dict[str, float] = {"song": 0.5, "artist": 0.3, "genre": 0.2}
SEED_LIMIT = 50  # top liked songs/artists/genres used to find candidates
CANDIDATE_LIMIT = 500
TOP_K = 10  # pick randomly (weighted) among this many best candidates
RECENT_MINUTES = 120  # don't repeat a song played in the channel this recently
# With nothing playing, the last song played in the channel within this window
# sets the genres to stay close to; older than that, the room starts fresh.
CONTEXT_MINUTES = 30
# The cutoff for "too low to play": candidates (and the songs, artists and
# genres used to find them) must score above it. NEUTRAL_SCORE is only the
# stand-in for things nobody in the room has reacted to, never a cutoff.
DISLIKE_THRESHOLD = 0.35

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
    # shares a genre with the song it follows (False: no match was acceptable,
    # or there was nothing to follow)
    cohesive: bool = False


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

    async def context_genres(
        self, channel_id: int, song_id: Optional[int] = None
    ) -> frozenset[int]:
        """Genres of the song the next pick should follow: `song_id` (the one
        playing) if given, else the channel's last play within
        CONTEXT_MINUTES. Spotify tags artists, not songs, so these are the
        song's artist's genres. Empty if there's nothing to follow."""
        genre_ids = await self.db.fetch_val(
            """
            SELECT ARRAY(
                SELECT ag.genre_id
                FROM songs s JOIN artist_genres ag ON ag.artist_id = s.artist_id
                WHERE s.id = COALESCE($1::int, (
                    SELECT p.song_id FROM plays p
                    WHERE p.channel_id = $2
                      AND p.started_at > now() - make_interval(mins => $3)
                    ORDER BY p.started_at DESC
                    LIMIT 1)))
            """,
            song_id,
            channel_id,
            CONTEXT_MINUTES,
        )
        return frozenset(genre_ids or [])

    async def candidates(
        self,
        channel_id: int,
        scores: dict[str, dict[int, float]],
        exclude_song_ids: Optional[list[int]] = None,
        context_genres: frozenset[int] = frozenset(),
    ) -> list[Candidate]:
        """Songs connected to anything the group likes or to the genres of
        the song being followed, minus recent plays and `exclude_song_ids`.
        Ordered so the CANDIDATE_LIMIT keeps the most relevant: genre
        matches with the followed song first, then the room's liked songs,
        then liked artists."""
        seeds = {kind: self.top_liked(scores[kind]) for kind in KINDS}
        # the followed song's genres find candidates even if the room
        # hasn't rated them yet (e.g. seeded songs in the same genre)
        genre_seeds = list(dict.fromkeys([*context_genres, *seeds["genre"]]))
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
            ORDER BY EXISTS (SELECT 1 FROM artist_genres
                             WHERE artist_id = s.artist_id
                               AND genre_id = ANY($8::int[])) DESC,
                     s.id = ANY($1::int[]) DESC,
                     s.artist_id = ANY($2::int[]) DESC
            LIMIT $6
            """,
            seeds["song"],
            seeds["artist"],
            genre_seeds,
            channel_id,
            RECENT_MINUTES,
            CANDIDATE_LIMIT,
            exclude_song_ids or [],
            list(context_genres),
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
        context_song_id: Optional[int] = None,
    ) -> Optional[Pick]:
        """Choose the next song for the room, or None if there isn't enough
        history yet (cold start) to pick anything the room likes.

        The pick follows on from `context_song_id` (the song playing now) or,
        without one, the channel's most recent play: songs sharing a genre
        with it are preferred, for some cohesion between plays.

        `exclude_song_ids` covers songs the recent-plays check can't see yet,
        e.g. the one playing right now while the next pick is prepared."""
        if not member_ids:
            return None
        scores = await self.group_scores(member_ids)
        if not any(scores.values()):
            return None
        context = await self.context_genres(channel_id, context_song_id)
        candidates = await self.candidates(
            channel_id, scores, exclude_song_ids, context
        )
        return self.choose(candidates, scores, rng or random.Random(), context)

    @staticmethod
    def top_liked(scores: dict[int, float]) -> list[int]:
        """The SEED_LIMIT best-scored items the room doesn't dislike: the
        songs, artists and genres to look for candidates around."""
        acceptable = [
            item for item, score in scores.items() if score > DISLIKE_THRESHOLD
        ]
        acceptable.sort(key=lambda item: scores[item], reverse=True)
        return acceptable[:SEED_LIMIT]

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
        context_genres: frozenset[int] = frozenset(),
    ) -> Optional[Pick]:
        """Weighted-random pick among the TOP_K best acceptable candidates.

        Acceptable: scoring above DISLIKE_THRESHOLD, and not a song the room
        dislikes specifically (its own song score below the threshold), even
        if its artist and genres would lift its total.

        Cohesion first: if any acceptable candidate shares a genre with
        `context_genres` (the song being followed), only those are drawn
        from; otherwise every acceptable candidate is. Weighting by margin
        over the threshold favors what the room likes most while keeping
        some variety."""
        ranked = sorted(
            (
                (cls.score_candidate(c, scores), c)
                for c in candidates
                if scores["song"].get(c.song_id, cls.NEUTRAL_SCORE) >= DISLIKE_THRESHOLD
            ),
            key=lambda pair: pair[0],
            reverse=True,
        )
        acceptable = [(s, c) for s, c in ranked if s > DISLIKE_THRESHOLD]
        cohesive = [(s, c) for s, c in acceptable if context_genres & set(c.genre_ids)]
        top = (cohesive or acceptable)[:TOP_K]
        if not top:
            return None
        score, chosen = rng.choices(
            top, weights=[s - DISLIKE_THRESHOLD for s, _ in top]
        )[0]
        return Pick(
            song_id=chosen.song_id,
            title=chosen.title,
            artist=chosen.artist,
            score=score,
            cohesive=bool(cohesive),
        )
