import random

import pytest

from taste.curator import Candidate, Curator, Pick, SEED_LIMIT, TOP_K


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


def test_top_liked_keeps_only_above_neutral_sorted():
    assert Curator.top_liked({1: 0.9, 2: 0.4, 3: 0.7, 4: 0.5}) == [1, 3]


def test_top_liked_is_capped():
    liked = {i: 0.6 + i / 10_000 for i in range(SEED_LIMIT + 10)}
    assert len(Curator.top_liked(liked)) == SEED_LIMIT


def test_choose_returns_none_when_nothing_above_neutral():
    assert Curator.choose([candidate(1)], scores(), random.Random(0)) is None


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
