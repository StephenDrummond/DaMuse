import random

import pytest

from taste.curator import (
    CONTEXT_MINUTES,
    DISAGREEMENT_WEIGHT,
    DISLIKE_THRESHOLD,
    SEED_LIMIT,
    TOP_K,
    UNDERSERVED_WEIGHT,
    Candidate,
    Curator,
    Pick,
    RoomTaste,
    empty_scores,
    estimate,
)


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

    assert Curator.choose([candidate(1)], RoomTaste.solo(s), random.Random(0)) is None


def test_choose_accepts_below_neutral_but_not_disliked():
    # the real case that stopped playback: liked song, artist and genres pulled
    # down by skips -> total 0.484, below neutral but well above the threshold
    c = candidate(4, artist_id=3, genre_ids=[1, 2])
    s = scores(song={4: 0.525}, artist={3: 0.454}, genre={1: 0.428, 2: 0.428})

    pick = Curator.choose([c], RoomTaste.solo(s), random.Random(0))

    assert pick is not None and pick.song_id == 4
    assert pick.score == pytest.approx(0.5 * 0.525 + 0.3 * 0.454 + 0.2 * 0.428)


def test_choose_prefers_higher_scores():
    better, worse = candidate(1, artist_id=1), candidate(2, artist_id=2)
    s = scores(song={1: 0.8, 2: 0.4}, artist={1: 0.8, 2: 0.4})
    rng = random.Random(0)

    picks = [
        Curator.choose([better, worse], RoomTaste.solo(s), rng) for _ in range(400)
    ]
    better_share = sum(p is not None and p.song_id == 1 for p in picks) / len(picks)

    # weights are margins over the threshold: 0.71 - 0.35 vs 0.43 - 0.35
    assert 0.75 < better_share < 0.9


def test_choose_excludes_group_disliked_song():
    # liked artist, but the room dislikes this specific song
    disliked = candidate(1, artist_id=2)
    s = scores(song={1: 0.2}, artist={2: 1.0})

    assert Curator.choose([disliked], RoomTaste.solo(s), random.Random(0)) is None


def test_choose_only_from_top_k():
    best = [candidate(i) for i in range(TOP_K)]
    worse = [candidate(100 + i) for i in range(5)]
    s = scores(
        song={**{i: 0.9 for i in range(TOP_K)}, **{100 + i: 0.6 for i in range(5)}}
    )

    rng = random.Random(1)
    choices = {Curator.choose(best + worse, RoomTaste.solo(s), rng) for _ in range(200)}

    assert None not in choices
    picks = {pick.song_id for pick in choices if pick is not None}

    assert picks <= set(range(TOP_K))


def test_choose_returns_pick_details():
    s = scores(song={7: 1.0})
    pick = Curator.choose(
        [candidate(7, artist_id=8)], RoomTaste.solo(s), random.Random(0)
    )

    assert pick is not None
    assert pick.score == pytest.approx(0.75)
    assert pick == Pick(song_id=7, title="song 7", artist="artist 8", score=pick.score)


@pytest.mark.asyncio
async def test_room_taste_keeps_each_members_scores(db):
    db.fetch.side_effect = [
        [{"user_id": 4, "item_id": 1, "score": 0.8}],  # song scores
        [{"user_id": 5, "item_id": 2, "score": 0.6}],  # artist scores
        [],  # genre scores
        [],  # recent plays (fairness)
    ]

    taste = await Curator(db).room_taste(42, [5, 4, 5])

    assert taste.scores == {
        4: {"song": {1: 0.8}, "artist": {}, "genre": {}},
        5: {"song": {}, "artist": {2: 0.6}, "genre": {}},
    }
    for call in db.fetch.await_args_list[:3]:
        assert call.args[1] == [4, 5]  # unique members, one query per table
    assert taste.weights == {}  # nothing played lately: everyone counts the same


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
        [{"user_id": 5, "item_id": 7, "score": 0.9}],  # song scores
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
    db.fetch.side_effect = [[{"user_id": 5, "item_id": 7, "score": 0.9}], [], [], []]

    await Curator(db).pick_next(42, [5], exclude_song_ids=[7])

    assert db.fetch.await_args_list[3].args[7] == [7]


# --- cohesion: prefer songs sharing a genre with what's playing -------------

ROCK, PROG, DISCO = 1, 2, 3


def test_choose_prefers_genre_matches_over_higher_scores():
    rock = candidate(1, artist_id=1, genre_ids=[ROCK])
    disco = candidate(2, artist_id=2, genre_ids=[DISCO])
    s = scores(song={1: 0.55, 2: 0.95})  # the room likes the disco song more

    picks = {
        Curator.choose(
            [rock, disco],
            RoomTaste.solo(s),
            random.Random(seed),
            frozenset({ROCK, PROG}),
        )
        for seed in range(50)
    }

    assert {p.song_id for p in picks if p} == {1}
    assert all(p is not None and p.cohesive for p in picks)


def test_choose_falls_back_when_no_genre_match_is_acceptable():
    disliked_rock = candidate(1, artist_id=1, genre_ids=[ROCK])
    disco = candidate(2, artist_id=2, genre_ids=[DISCO])
    s = scores(song={1: 0.2, 2: 0.8})  # the only rock song is disliked

    pick = Curator.choose(
        [disliked_rock, disco], RoomTaste.solo(s), random.Random(0), frozenset({ROCK})
    )

    assert pick is not None and pick.song_id == 2
    assert pick.cohesive is False  # music keeps going, just without a match


def test_choose_without_context_uses_every_acceptable_candidate():
    rock = candidate(1, artist_id=1, genre_ids=[ROCK])
    disco = candidate(2, artist_id=2, genre_ids=[DISCO])
    s = scores(song={1: 0.8, 2: 0.8})

    picks = {
        Curator.choose([rock, disco], RoomTaste.solo(s), random.Random(seed))
        for seed in range(50)
    }

    assert {p.song_id for p in picks if p} == {1, 2}
    assert not any(p.cohesive for p in picks if p)


def test_choose_draws_only_from_matches_even_below_neutral():
    meh_rock = candidate(1, artist_id=1, genre_ids=[ROCK])
    great_disco = candidate(2, artist_id=2, genre_ids=[DISCO])
    s = scores(song={1: 0.42, 2: 1.0}, artist={1: 0.45})

    pick = Curator.choose(
        [meh_rock, great_disco], RoomTaste.solo(s), random.Random(0), frozenset({ROCK})
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
    db.fetch.side_effect = [[{"user_id": 5, "item_id": 7, "score": 0.9}], [], [], []]

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
        [
            {"user_id": 5, "item_id": k, "score": v}
            for k, v in (song_scores or {}).items()
        ],
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


# --- group taste: least misery and fairness ----------------------------------

ALICE, BOB, CAROL = 1, 2, 3


def room(**members):
    """RoomTaste from member=scores(...) keyword arguments (alice, bob, carol)."""
    ids = {"alice": ALICE, "bob": BOB, "carol": CAROL}
    return RoomTaste({ids[name]: s for name, s in members.items()})


def test_one_member_room_scores_like_that_member():
    c = candidate(1, artist_id=2)
    s = scores(song={1: 0.8}, artist={2: 0.6})

    assert RoomTaste.solo(s).evaluate(c) == pytest.approx(estimate(c, s))


def test_anyone_disliking_the_song_vetoes_it():
    c = candidate(1)
    taste = room(
        alice=scores(song={1: 1.0}),
        bob=scores(song={1: 1.0}),
        carol=scores(song={1: 0.3}),
    )

    assert taste.evaluate(c) is None  # two love it, one dislikes it: not played


def test_anyone_who_would_dislike_it_overall_vetoes_it():
    c = candidate(1, artist_id=2, genre_ids=[9])
    # bob never rated the song, but dislikes the artist and the genre
    taste = room(
        alice=scores(song={1: 1.0}),
        bob=scores(artist={2: 0.1}, genre={9: 0.1}),
    )

    assert estimate(c, taste.scores[BOB]) <= DISLIKE_THRESHOLD
    assert taste.evaluate(c) is None


def test_disagreement_lowers_the_room_score():
    c = candidate(1)
    agree = room(alice=scores(song={1: 0.7}), bob=scores(song={1: 0.7}))
    split = room(alice=scores(song={1: 1.0}), bob=scores(song={1: 0.4}))
    alice, bob = 0.5 * 1.0 + 0.15 + 0.1, 0.5 * 0.4 + 0.15 + 0.1  # song + neutral rest

    # same average song score (0.7), but the split room is less happy as a whole
    assert agree.evaluate(c) == pytest.approx(0.5 * 0.7 + 0.15 + 0.1)
    average = (alice + bob) / 2
    expected = average - DISAGREEMENT_WEIGHT * (average - bob)
    assert split.evaluate(c) == pytest.approx(expected)
    assert split.evaluate(c) < agree.evaluate(c)


def test_choose_prefers_what_everyone_likes_over_what_one_loves():
    shared = candidate(1, artist_id=1)
    polarizing = candidate(2, artist_id=2)
    taste = room(
        alice=scores(song={1: 0.7, 2: 1.0}),
        bob=scores(song={1: 0.7, 2: 0.4}),
    )
    rng = random.Random(0)

    picks = [Curator.choose([shared, polarizing], taste, rng) for _ in range(400)]
    shared_share = sum(p is not None and p.song_id == 1 for p in picks) / len(picks)

    assert shared_share > 0.55


def test_underserved_member_counts_more():
    c = candidate(1, artist_id=2)
    taste = room(alice=scores(song={1: 0.9}), bob=scores(song={1: 0.4}))
    even = taste.evaluate(c)

    taste.weights = {BOB: UNDERSERVED_WEIGHT}
    favoring_bob = taste.evaluate(c)

    assert favoring_bob is not None and even is not None
    assert favoring_bob < even  # bob's lower opinion now weighs more


def test_seeds_come_from_every_member():
    # alice has lots of history; bob's single favorite still makes the seeds
    alice = scores(song={i: 0.9 for i in range(100, 100 + SEED_LIMIT)})
    bob = scores(song={7: 0.8})

    seeds = room(alice=alice, bob=bob).seeds("song")

    assert 7 in seeds
    assert len(seeds) == SEED_LIMIT + 1


def test_empty_room_rates_everything_neutral():
    assert RoomTaste({}).evaluate(candidate(1)) == pytest.approx(0.5)
    assert RoomTaste({ALICE: empty_scores()}).is_empty()


def song_rows(*cands):
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


@pytest.mark.asyncio
async def test_fairness_flags_the_member_recent_songs_suited_least(db):
    rock = candidate(1, artist_id=1, genre_ids=[ROCK])
    taste = room(
        alice=scores(genre={ROCK: 0.9}),
        bob=scores(genre={ROCK: 0.9}),
        carol=scores(genre={ROCK: 0.2}),
    )
    db.fetch.return_value = song_rows(rock, rock, rock)  # the last plays were rock

    weights = await Curator(db).fairness_weights(42, taste)

    assert weights == {CAROL: UNDERSERVED_WEIGHT}


@pytest.mark.asyncio
async def test_fairness_needs_two_members_and_recent_plays(db):
    solo = room(alice=scores())
    pair = room(alice=scores(), bob=scores())
    db.fetch.return_value = []

    assert await Curator(db).fairness_weights(42, solo) == {}
    db.fetch.assert_not_awaited()
    assert await Curator(db).fairness_weights(42, pair) == {}


@pytest.mark.asyncio
async def test_fairness_leaves_an_evenly_served_room_alone(db):
    taste = room(alice=scores(genre={ROCK: 0.7}), bob=scores(genre={ROCK: 0.7}))
    db.fetch.return_value = song_rows(candidate(1, genre_ids=[ROCK]))

    assert await Curator(db).fairness_weights(42, taste) == {}
