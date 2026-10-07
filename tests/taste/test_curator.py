import random

import pytest

from taste.curator import CONTEXT_MINUTES, Candidate, Curator, Pick, SEED_LIMIT, TOP_K


def candidate(song_id, artist_id=100, genre_ids=()):
    return Candidate(
        song_id=song_id,
        title=f"song {song_id}",
        artist=f"artist {artist_id}",
        artist_id=artist_id,
        genre_ids=list(genre_ids),
    )


def scores(song=None, artist=None, genre=None):
    return {"song": song or {}, "artist": artist or {}, "genre": genre or {}}


def test_score_candidate_unknown_is_neutral():
    assert Curator.score_candidate(candidate(1), scores()) == pytest.approx(0.5)


def test_score_candidate_weights_levels():
    c = candidate(1, artist_id=2, genre_ids=[3, 4])
    s = scores(song={1: 1.0}, artist={2: 0.0}, genre={3: 1.0})  # genre 4 neutral

    # 0.5 * 1.0 + 0.3 * 0.0 + 0.2 * mean(1.0, 0.5)
    assert Curator.score_candidate(c, s) == pytest.approx(0.65)


def test_top_liked_keeps_everything_above_dislike_threshold_sorted():
    # 0.40 and 0.50 are below neutral / neutral but not disliked: still seeds
    assert Curator.top_liked({1: 0.9, 2: 0.4, 3: 0.7, 4: 0.5, 5: 0.3}) == [1, 3, 4, 2]


def test_top_liked_is_capped():
    liked = {i: 0.6 + i / 10_000 for i in range(SEED_LIMIT + 10)}
    assert len(Curator.top_liked(liked)) == SEED_LIMIT


def test_choose_returns_none_when_everything_is_disliked():
    s = scores(song={1: 0.36}, artist={100: 0.2})  # total 0.18 + 0.06 + 0.1 = 0.34

    assert Curator.choose([candidate(1)], s, random.Random(0)) is None


def test_choose_accepts_below_neutral_but_not_disliked():
    # the real case that stopped playback: liked song, artist and genres pulled
    # down by skips -> total 0.484, below neutral but well above the threshold
    c = candidate(4, artist_id=3, genre_ids=[1, 2])
    s = scores(song={4: 0.525}, artist={3: 0.454}, genre={1: 0.428, 2: 0.428})

    pick = Curator.choose([c], s, random.Random(0))

    assert pick is not None and pick.song_id == 4
    assert pick.score == pytest.approx(0.5 * 0.525 + 0.3 * 0.454 + 0.2 * 0.428)


def test_choose_prefers_higher_scores():
    better, worse = candidate(1, artist_id=1), candidate(2, artist_id=2)
    s = scores(song={1: 0.8, 2: 0.4}, artist={1: 0.8, 2: 0.4})
    rng = random.Random(0)

    picks = [Curator.choose([better, worse], s, rng) for _ in range(400)]
    better_share = sum(p is not None and p.song_id == 1 for p in picks) / len(picks)

    # weights are margins over the threshold: 0.71 - 0.35 vs 0.43 - 0.35
    assert 0.75 < better_share < 0.9


def test_choose_excludes_group_disliked_song():
    # liked artist, but the room dislikes this specific song
    disliked = candidate(1, artist_id=2)
    s = scores(song={1: 0.2}, artist={2: 1.0})

    assert Curator.choose([disliked], s, random.Random(0)) is None


def test_choose_only_from_top_k():
    best = [candidate(i) for i in range(TOP_K)]
    worse = [candidate(100 + i) for i in range(5)]
    s = scores(
        song={**{i: 0.9 for i in range(TOP_K)}, **{100 + i: 0.6 for i in range(5)}}
    )

    rng = random.Random(1)
    choices = {Curator.choose(best + worse, s, rng) for _ in range(200)}

    assert None not in choices
    picks = {pick.song_id for pick in choices if pick is not None}

    assert picks <= set(range(TOP_K))


def test_choose_returns_pick_details():
    s = scores(song={7: 1.0})
    pick = Curator.choose([candidate(7, artist_id=8)], s, random.Random(0))

    assert pick is not None
    assert pick.score == pytest.approx(0.75)
    assert pick == Pick(song_id=7, title="song 7", artist="artist 8", score=pick.score)


@pytest.mark.asyncio
async def test_group_scores_queries_each_table(db):
    db.fetch.side_effect = [
        [{"item_id": 1, "score": 0.8}],
        [{"item_id": 2, "score": 0.6}],
        [],
    ]

    result = await Curator(db).group_scores([5, 4, 5])

    assert result == {"song": {1: 0.8}, "artist": {2: 0.6}, "genre": {}}
    for call in db.fetch.await_args_list:
        assert call.args[1:] == ([4, 5], 2)  # unique members, group size


@pytest.mark.asyncio
async def test_pick_next_no_members(db):
    assert await Curator(db).pick_next(1, []) is None
    db.fetch.assert_not_awaited()


@pytest.mark.asyncio
async def test_pick_next_cold_start(db):
    db.fetch.return_value = []  # no one has any history

    assert await Curator(db).pick_next(1, [5]) is None
    assert db.fetch.await_count == 3  # score queries only, no candidate query


@pytest.mark.asyncio
async def test_pick_next_end_to_end(db):
    db.fetch.side_effect = [
        [{"item_id": 7, "score": 0.9}],  # song scores
        [],  # artist scores
        [],  # genre scores
        [  # candidates
            {
                "song_id": 7,
                "title": "Money",
                "artist": "Pink Floyd",
                "artist_id": 8,
                "genre_ids": [],
            }
        ],
    ]

    pick = await Curator(db).pick_next(42, [5], rng=random.Random(0))

    assert pick is not None and pick.song_id == 7
    candidate_args = db.fetch.await_args_list[3].args
    assert candidate_args[1] == [7]  # liked songs seed the candidates
    assert candidate_args[4] == 42  # recent plays excluded for this channel
    assert candidate_args[7] == []  # nothing explicitly excluded


@pytest.mark.asyncio
async def test_pick_next_passes_exclusions_to_candidates(db):
    db.fetch.side_effect = [[{"item_id": 7, "score": 0.9}], [], [], []]

    await Curator(db).pick_next(42, [5], exclude_song_ids=[7])

    assert db.fetch.await_args_list[3].args[7] == [7]


# --- cohesion: prefer songs sharing a genre with what's playing -------------

ROCK, PROG, DISCO = 1, 2, 3


def test_choose_prefers_genre_matches_over_higher_scores():
    rock = candidate(1, artist_id=1, genre_ids=[ROCK])
    disco = candidate(2, artist_id=2, genre_ids=[DISCO])
    s = scores(song={1: 0.55, 2: 0.95})  # the room likes the disco song more

    picks = {
        Curator.choose([rock, disco], s, random.Random(seed), frozenset({ROCK, PROG}))
        for seed in range(50)
    }

    assert {p.song_id for p in picks if p} == {1}
    assert all(p is not None and p.cohesive for p in picks)


def test_choose_falls_back_when_no_genre_match_is_acceptable():
    disliked_rock = candidate(1, artist_id=1, genre_ids=[ROCK])
    disco = candidate(2, artist_id=2, genre_ids=[DISCO])
    s = scores(song={1: 0.2, 2: 0.8})  # the only rock song is disliked

    pick = Curator.choose(
        [disliked_rock, disco], s, random.Random(0), frozenset({ROCK})
    )

    assert pick is not None and pick.song_id == 2
    assert pick.cohesive is False  # music keeps going, just without a match


def test_choose_without_context_uses_every_acceptable_candidate():
    rock = candidate(1, artist_id=1, genre_ids=[ROCK])
    disco = candidate(2, artist_id=2, genre_ids=[DISCO])
    s = scores(song={1: 0.8, 2: 0.8})

    picks = {
        Curator.choose([rock, disco], s, random.Random(seed)) for seed in range(50)
    }

    assert {p.song_id for p in picks if p} == {1, 2}
    assert not any(p.cohesive for p in picks if p)


def test_choose_draws_only_from_matches_even_below_neutral():
    meh_rock = candidate(1, artist_id=1, genre_ids=[ROCK])
    great_disco = candidate(2, artist_id=2, genre_ids=[DISCO])
    s = scores(song={1: 0.42, 2: 1.0}, artist={1: 0.45})

    pick = Curator.choose(
        [meh_rock, great_disco], s, random.Random(0), frozenset({ROCK})
    )

    assert pick is not None and pick.song_id == 1


@pytest.mark.asyncio
async def test_context_genres_uses_given_song(db):
    db.fetch_val.return_value = [ROCK, PROG]

    assert await Curator(db).context_genres(42, song_id=7) == {ROCK, PROG}
    assert db.fetch_val.await_args.args[1:] == (7, 42, CONTEXT_MINUTES)


@pytest.mark.asyncio
async def test_context_genres_nothing_to_follow(db):
    db.fetch_val.return_value = []

    assert await Curator(db).context_genres(42) == frozenset()


@pytest.mark.asyncio
async def test_pick_next_passes_context_to_candidates(db):
    db.fetch_val.return_value = [ROCK]
    db.fetch.side_effect = [[{"item_id": 7, "score": 0.9}], [], [], []]

    await Curator(db).pick_next(42, [5], context_song_id=3)

    candidate_args = db.fetch.await_args_list[3].args
    assert candidate_args[3] == [ROCK]  # context genres seed the search
    assert candidate_args[8] == [ROCK]  # and rank first
    assert db.fetch_val.await_args.args[1] == 3


# --- !switch -----------------------------------------------------------------

HOUSE, TECHNO = 4, 5


def candidate_rows(*cands):
    return [
        {
            "song_id": c.song_id,
            "title": c.title,
            "artist": c.artist,
            "artist_id": c.artist_id,
            "genre_ids": c.genre_ids,
        }
        for c in cands
    ]


def switch_db(db, current_genres, cands, song_scores=None, genre_name="house"):
    """Wire the fake db for pick_switch: scores, current genres, candidates."""
    db.fetch.side_effect = [
        [{"item_id": k, "score": v} for k, v in (song_scores or {}).items()],
        [],
        [],
        candidate_rows(*cands),
    ]
    db.fetch_val.side_effect = [list(current_genres), genre_name]


@pytest.mark.asyncio
async def test_switch_never_picks_the_current_genre(db):
    rock = candidate(1, artist_id=1, genre_ids=[ROCK])
    rock_and_house = candidate(2, artist_id=2, genre_ids=[ROCK, HOUSE])
    house = candidate(3, artist_id=3, genre_ids=[HOUSE])
    switch_db(db, {ROCK}, [rock, rock_and_house, house])

    pick = await Curator(db).pick_switch(10, [5], rng=random.Random(0))

    # anything sharing a genre with the current song is out, even partly
    assert pick is not None and pick.song_id == 3
    assert pick.genre == "house"


@pytest.mark.asyncio
async def test_switch_picks_genre_at_random(db):
    house = candidate(1, artist_id=1, genre_ids=[HOUSE])
    techno = candidate(2, artist_id=2, genre_ids=[TECHNO])
    picked = set()
    for seed in range(40):
        switch_db(db, {ROCK}, [house, techno])
        pick = await Curator(db).pick_switch(10, [5], rng=random.Random(seed))
        assert pick is not None
        picked.add(pick.song_id)

    assert picked == {1, 2}


@pytest.mark.asyncio
async def test_switch_skips_disliked_genres(db):
    disliked_house = candidate(1, artist_id=1, genre_ids=[HOUSE])
    techno = candidate(2, artist_id=2, genre_ids=[TECHNO])
    switch_db(db, {ROCK}, [disliked_house, techno], song_scores={1: 0.1})

    pick = await Curator(db).pick_switch(10, [5], rng=random.Random(0))

    assert pick is not None and pick.song_id == 2


@pytest.mark.asyncio
async def test_switch_with_nowhere_to_go(db):
    switch_db(db, {ROCK}, [candidate(1, artist_id=1, genre_ids=[ROCK])])

    assert await Curator(db).pick_switch(10, [5]) is None


@pytest.mark.asyncio
async def test_switch_needs_listeners(db):
    assert await Curator(db).pick_switch(10, []) is None
    db.fetch.assert_not_awaited()


@pytest.mark.asyncio
async def test_similar_picks_the_artist_or_their_genres(db):
    by_artist = candidate(1, artist_id=7, genre_ids=[HOUSE])
    same_genre = candidate(2, artist_id=8, genre_ids=[HOUSE, TECHNO])
    unrelated = candidate(3, artist_id=9, genre_ids=[ROCK])
    picks = set()
    for seed in range(40):
        db.fetch.side_effect = [
            [],
            [],
            [],
            candidate_rows(by_artist, same_genre, unrelated),
        ]
        pick = await Curator(db).pick_similar(
            10, [5], artist_id=7, genre_ids=[HOUSE], rng=random.Random(seed)
        )
        assert pick is not None
        picks.add(pick.song_id)

    assert picks == {1, 2}  # never the unrelated rock song


@pytest.mark.asyncio
async def test_similar_seeds_the_artist_into_the_search(db):
    db.fetch.side_effect = [[], [], [], []]

    await Curator(db).pick_similar(10, [5], artist_id=7, genre_ids=[HOUSE])

    candidate_args = db.fetch.await_args_list[3].args
    assert 7 in candidate_args[2]  # artist seeds
    assert HOUSE in candidate_args[3] and candidate_args[8] == [HOUSE]


@pytest.mark.asyncio
async def test_similar_without_genres_sticks_to_the_artist(db):
    by_artist = candidate(1, artist_id=7, genre_ids=[])
    other = candidate(2, artist_id=8, genre_ids=[ROCK])
    db.fetch.side_effect = [[], [], [], candidate_rows(by_artist, other)]

    pick = await Curator(db).pick_similar(
        10, [5], artist_id=7, genre_ids=[], rng=random.Random(0)
    )

    assert pick is not None and pick.song_id == 1


@pytest.mark.asyncio
async def test_similar_works_with_nobody_listening(db):
    db.fetch.side_effect = [candidate_rows(candidate(1, artist_id=7, genre_ids=[]))]

    pick = await Curator(db).pick_similar(10, [], artist_id=7, genre_ids=[])

    assert pick is not None  # no history needed: unrated songs count as neutral
