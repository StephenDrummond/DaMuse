import asyncio
import random
from dataclasses import dataclass, field, replace
from typing import Optional

from db.client import DBClient

# How much each level of taste counts toward one member's estimate for a song.
WEIGHTS: dict[str, float] = {"song": 0.5, "artist": 0.3, "genre": 0.2}
SEED_LIMIT = 50  # each member's top songs/artists/genres used to find candidates
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

# Least misery. The room's score for a song sits this far from the (weighted)
# average toward the least happy member: 0 = plain average, 1 = the least happy
# member decides. Anything a present member would score at or below
# DISLIKE_THRESHOLD is never played, however much the others like it.
DISAGREEMENT_WEIGHT = 0.5

# Fairness. How well each present member's taste was served by the channel's
# last FAIRNESS_PLAYS songs (within FAIRNESS_MINUTES); anyone noticeably below
# the room's average (by more than FAIRNESS_MARGIN) counts UNDERSERVED_WEIGHT
# times as much in the next pick, so the music drifts back toward them.
FAIRNESS_PLAYS = 5
FAIRNESS_MINUTES = 60
FAIRNESS_MARGIN = 0.02
UNDERSERVED_WEIGHT = 2.0

KINDS: dict[str, str] = {
    "song": "song_user_likes",
    "artist": "artist_user_likes",
    "genre": "genre_user_likes",
}

Scores = dict[str, dict[int, float]]  # kind ("song"/"artist"/"genre") -> item -> score


def empty_scores() -> Scores:
    return {kind: {} for kind in KINDS}


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
    # for !switch: the genre the room was switched to
    genre: Optional[str] = None


def estimate(candidate: Candidate, scores: Scores) -> float:
    """How much one member would like `candidate`, from their song, artist
    and genre scores (anything they never reacted to counts as neutral)."""
    neutral = DBClient.NEUTRAL_SCORE
    genre_scores = [scores["genre"].get(g, neutral) for g in candidate.genre_ids]
    parts = {
        "song": scores["song"].get(candidate.song_id, neutral),
        "artist": scores["artist"].get(candidate.artist_id, neutral),
        "genre": sum(genre_scores) / len(genre_scores) if genre_scores else neutral,
    }
    return sum(WEIGHTS[kind] * value for kind, value in parts.items())


@dataclass
class RoomTaste:
    """Everyone in the voice channel: each member's own scores, and how much
    each member counts for this pick (1 unless underserved lately)."""

    scores: dict[int, Scores]  # member id -> their scores
    weights: dict[int, float] = field(default_factory=dict)

    @classmethod
    def solo(cls, scores: Scores, member_id: int = 0) -> "RoomTaste":
        return cls({member_id: scores})

    @property
    def members(self) -> list[int]:
        return list(self.scores)

    def is_empty(self) -> bool:
        """True if nobody present has reacted to anything yet (cold start)."""
        return not any(any(s.values()) for s in self.scores.values())

    def weight(self, member_id: int) -> float:
        return self.weights.get(member_id, 1.0)

    def seeds(self, kind: str) -> list[int]:
        """The items to look for candidates around: every member's own top
        SEED_LIMIT, so one heavy listener's history can't crowd out the rest."""
        seeds: dict[int, None] = {}
        for member_scores in self.scores.values():
            seeds.update(dict.fromkeys(Curator.top_liked(member_scores[kind])))
        return list(seeds)

    def evaluate(self, candidate: Candidate) -> Optional[float]:
        """The room's score for `candidate`, or None if it must not play.

        Vetoed if any member dislikes the song itself (its own song score is
        below DISLIKE_THRESHOLD), or would score it at or below the threshold
        overall. Otherwise: the weighted average of every member's estimate,
        pulled DISAGREEMENT_WEIGHT of the way toward the least happy member.
        With one member this is simply their estimate."""
        if not self.scores:  # nobody listening: everything is neutral
            score = estimate(candidate, empty_scores())
            return score if score > DISLIKE_THRESHOLD else None

        neutral = DBClient.NEUTRAL_SCORE
        estimates: dict[int, float] = {}
        for member_id, member_scores in self.scores.items():
            if (
                member_scores["song"].get(candidate.song_id, neutral)
                < DISLIKE_THRESHOLD
            ):
                return None
            estimates[member_id] = estimate(candidate, member_scores)

        least = min(estimates.values())
        if least <= DISLIKE_THRESHOLD:
            return None
        total_weight = sum(self.weight(m) for m in estimates)
        average = (
            sum(self.weight(m) * score for m, score in estimates.items()) / total_weight
        )
        return average - DISAGREEMENT_WEIGHT * (average - least)


CANDIDATE_COLUMNS = """
    s.id AS song_id, s.title, a.name AS artist, s.artist_id,
    ARRAY(SELECT genre_id FROM artist_genres
          WHERE artist_id = s.artist_id) AS genre_ids
"""


def candidate_from_row(row) -> Candidate:
    return Candidate(
        song_id=row["song_id"],
        title=row["title"],
        artist=row["artist"],
        artist_id=row["artist_id"],
        genre_ids=list(row["genre_ids"]),
    )


class Curator(DBClient):
    """Picks what a voice channel should hear next for everyone in it: no
    song anyone present would dislike, disagreement counts against a song,
    and whoever has been least served lately counts extra. Stateless:
    membership comes from Discord and scores from Postgres on every call, so
    any process can curate any channel."""

    async def room_taste(self, channel_id: int, member_ids: list[int]) -> RoomTaste:
        """Each member's scores, plus fairness weights from recent plays."""
        members = sorted(set(member_ids))
        scores: dict[int, Scores] = {m: empty_scores() for m in members}

        async def fetch(kind: str, table: str) -> None:
            _, _, id_column = self.PREFERENCE_TABLE_MAPPING[table]
            rows = await self.db.fetch(
                f"""
                SELECT user_id, {id_column} AS item_id, preference_score AS score
                FROM {table}
                WHERE user_id = ANY($1::bigint[])
                """,
                members,
            )
            for row in rows:
                scores[row["user_id"]][kind][row["item_id"]] = row["score"]

        if members:
            await asyncio.gather(*(fetch(kind, table) for kind, table in KINDS.items()))
        taste = RoomTaste(scores)
        taste.weights = await self.fairness_weights(channel_id, taste)
        return taste

    async def fairness_weights(
        self, channel_id: int, taste: RoomTaste
    ) -> dict[int, float]:
        """UNDERSERVED_WEIGHT for each member the channel's recent songs suited
        noticeably worse than the room on average; empty if everyone is even,
        there's one member, or nothing played lately."""
        if len(taste.members) < 2:
            return {}
        rows = await self.db.fetch(
            f"""
            SELECT {CANDIDATE_COLUMNS}
            FROM plays p
            JOIN songs s ON s.id = p.song_id
            JOIN artists a ON a.id = s.artist_id
            WHERE p.channel_id = $1
              AND p.started_at > now() - make_interval(mins => $2)
            ORDER BY p.started_at DESC
            LIMIT $3
            """,
            channel_id,
            FAIRNESS_MINUTES,
            FAIRNESS_PLAYS,
        )
        recent = [candidate_from_row(row) for row in rows]
        if not recent:
            return {}
        satisfaction = {
            member_id: sum(estimate(song, member_scores) for song in recent)
            / len(recent)
            for member_id, member_scores in taste.scores.items()
        }
        room_average = sum(satisfaction.values()) / len(satisfaction)
        return {
            member_id: UNDERSERVED_WEIGHT
            for member_id, served in satisfaction.items()
            if served < room_average - FAIRNESS_MARGIN
        }

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
        taste: RoomTaste,
        exclude_song_ids: Optional[list[int]] = None,
        context_genres: frozenset[int] = frozenset(),
        extra_artist_ids: tuple[int, ...] = (),
    ) -> list[Candidate]:
        """Songs connected to anything a member likes or to the genres of the
        song being followed, minus recent plays and `exclude_song_ids`.
        Ordered so the CANDIDATE_LIMIT keeps the most relevant: genre matches
        with the followed song first, then liked songs, then liked artists."""
        # the followed song's genres find candidates even if nobody has
        # rated them yet (e.g. seeded songs in the same genre)
        genre_seeds = list(dict.fromkeys([*context_genres, *taste.seeds("genre")]))
        artist_seeds = list(dict.fromkeys([*extra_artist_ids, *taste.seeds("artist")]))
        rows = await self.db.fetch(
            f"""
            SELECT {CANDIDATE_COLUMNS}
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
            taste.seeds("song"),
            artist_seeds,
            genre_seeds,
            channel_id,
            RECENT_MINUTES,
            CANDIDATE_LIMIT,
            exclude_song_ids or [],
            list(context_genres),
        )
        return [candidate_from_row(row) for row in rows]

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
        taste = await self.room_taste(channel_id, member_ids)
        if taste.is_empty():
            return None
        context = await self.context_genres(channel_id, context_song_id)
        candidates = await self.candidates(channel_id, taste, exclude_song_ids, context)
        return self.choose(candidates, taste, rng or random.Random(), context)

    async def pick_switch(
        self,
        channel_id: int,
        member_ids: list[int],
        current_song_id: Optional[int] = None,
        exclude_song_ids: Optional[list[int]] = None,
        rng: Optional[random.Random] = None,
    ) -> Optional[Pick]:
        """For !switch: leave the current genre for a random new one.

        The new genre is chosen at random among genres that have at least
        one acceptable song sharing no genre with the current song (the one
        playing, else the channel's last play); the song within it is chosen
        by the room's taste as usual. None if there's nowhere to switch to."""
        if not member_ids:
            return None
        rng = rng or random.Random()
        taste = await self.room_taste(channel_id, member_ids)
        current = await self.context_genres(channel_id, current_song_id)
        candidates = await self.candidates(channel_id, taste, exclude_song_ids)

        elsewhere = [
            c for c in candidates if c.genre_ids and not current & set(c.genre_ids)
        ]
        acceptable = [c for _, c in self.acceptable(elsewhere, taste)]
        genres = sorted({g for c in acceptable for g in c.genre_ids})
        if not genres:
            return None
        genre = rng.choice(genres)

        pick = self.choose(
            [c for c in acceptable if genre in c.genre_ids],
            taste,
            rng,
            frozenset({genre}),
        )
        if pick is None:
            return None
        name = await self.db.fetch_val("SELECT name FROM genres WHERE id = $1", genre)
        return replace(pick, genre=name)

    async def pick_similar(
        self,
        channel_id: int,
        member_ids: list[int],
        artist_id: int,
        genre_ids: list[int],
        exclude_song_ids: Optional[list[int]] = None,
        rng: Optional[random.Random] = None,
    ) -> Optional[Pick]:
        """For !switch <artist>: a song by the artist or sharing their
        genres, chosen by the room's taste. Songs nobody has rated count as
        neutral, so this works even with no history. If the artist has no
        genres on Spotify, only their own songs qualify."""
        genres = frozenset(genre_ids)
        taste = await self.room_taste(channel_id, member_ids)
        candidates = await self.candidates(
            channel_id,
            taste,
            exclude_song_ids,
            genres,
            extra_artist_ids=(artist_id,),
        )
        similar = [
            c
            for c in candidates
            if c.artist_id == artist_id or genres & set(c.genre_ids)
        ]
        return self.choose(similar, taste, rng or random.Random(), genres)

    @staticmethod
    def top_liked(scores: dict[int, float]) -> list[int]:
        """The SEED_LIMIT best-scored items not disliked: the songs, artists
        and genres to look for candidates around."""
        acceptable = [
            item for item, score in scores.items() if score > DISLIKE_THRESHOLD
        ]
        acceptable.sort(key=lambda item: scores[item], reverse=True)
        return acceptable[:SEED_LIMIT]

    @staticmethod
    def score_candidate(candidate: Candidate, scores: Scores) -> float:
        """One member's estimate for `candidate` (see `estimate`)."""
        return estimate(candidate, scores)

    @staticmethod
    def acceptable(
        candidates: list[Candidate], taste: RoomTaste
    ) -> list[tuple[float, Candidate]]:
        """(room score, candidate) pairs that may be played, best first; see
        RoomTaste.evaluate for what's vetoed."""
        scored = ((taste.evaluate(c), c) for c in candidates)
        return sorted(
            ((s, c) for s, c in scored if s is not None),
            key=lambda pair: pair[0],
            reverse=True,
        )

    @classmethod
    def choose(
        cls,
        candidates: list[Candidate],
        taste: RoomTaste,
        rng: random.Random,
        context_genres: frozenset[int] = frozenset(),
    ) -> Optional[Pick]:
        """Weighted-random pick among the TOP_K best acceptable candidates.

        Cohesion first: if any acceptable candidate shares a genre with
        `context_genres` (the song being followed), only those are drawn
        from; otherwise every acceptable candidate is. Weighting by margin
        over DISLIKE_THRESHOLD favors what the room likes most while keeping
        some variety."""
        acceptable = cls.acceptable(candidates, taste)
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
