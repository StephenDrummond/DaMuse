"""Seeding against real Postgres: claiming, re-seed timing, de-duplication,
and how seeded songs reach the Curator."""

import asyncio
import random
from unittest.mock import AsyncMock

import pytest

from taste.curator import Curator
from taste.librarian import Librarian
from taste.profiler import Profiler
from taste.seeder import ARTISTS_PER_ROUND, RESEED_AFTER_DAYS, Seeder

ALICE = 1001


def fake_spotify():
    spotify = AsyncMock()
    spotify.find_artist.return_value = {
        "id": "pf",
        "name": "Pink Floyd",
        "genres": ["progressive rock"],
    }
    spotify.get_artist.return_value = spotify.find_artist.return_value
    spotify.artist_top_tracks.return_value = [
        {"id": "t-money", "name": "Money", "artist_ids": ["pf"]},
        {"id": "t-time", "name": "Time", "artist_ids": ["pf"]},
        {"id": "t-wish", "name": "Wish You Were Here", "artist_ids": ["pf"]},
        {"id": "t-feat", "name": "Someone Else's Hit", "artist_ids": ["x", "pf"]},
    ]
    return spotify


@pytest.fixture
def librarian(pg):
    return Librarian(pg)


@pytest.fixture
def spotify():
    return fake_spotify()


@pytest.fixture
def seeder(pg, spotify, librarian):
    return Seeder(pg, spotify, librarian)


@pytest.mark.asyncio
async def test_seeding_adds_top_tracks_once(seeder, librarian, pg):
    # Money was already played (registered without a Spotify id)
    await librarian.register_track("Money", "Pink Floyd", ["progressive rock"])

    assert await seeder.seed_round() == 1

    rows = await pg.fetch("SELECT title, spotify_id, source FROM songs ORDER BY title")
    assert [(r["title"], r["spotify_id"], r["source"]) for r in rows] == [
        ("Money", "t-money", "played"),  # id filled in, source kept
        ("Time", "t-time", "top_tracks"),
        ("Wish You Were Here", "t-wish", "top_tracks"),
    ]  # the feature on another artist's song was skipped
    artist = await pg.fetch_row("SELECT spotify_id, seeded_at FROM artists")
    assert artist["spotify_id"] == "pf"
    assert artist["seeded_at"] is not None

    # nothing left to claim until RESEED_AFTER_DAYS pass
    assert await seeder.seed_round() == 0


@pytest.mark.asyncio
async def test_reseeds_after_interval_without_duplicates(seeder, librarian, pg):
    await librarian.register_track("Money", "Pink Floyd", [])
    await seeder.seed_round()
    await pg.execute(
        "UPDATE artists SET seeded_at = now() - make_interval(days => $1)",
        RESEED_AFTER_DAYS + 1,
    )

    assert await seeder.seed_round() == 1
    assert await pg.fetch_val("SELECT count(*) FROM songs") == 3


@pytest.mark.asyncio
async def test_claims_unseeded_artists_first_in_batches(seeder, librarian, pg):
    for i in range(ARTISTS_PER_ROUND + 2):
        await librarian.register_track(f"Song {i}", f"Artist {i}", [])
    await pg.execute(
        "UPDATE artists SET seeded_at = now() - interval '100 days' "
        "WHERE name = 'Artist 0'"
    )

    first = await seeder.claim_artists()
    second = await seeder.claim_artists()

    assert len(first) == ARTISTS_PER_ROUND
    assert "Artist 0" not in {a.name for a in first}  # never-seeded come first
    assert {a.name for a in second} >= {"Artist 0"}
    assert not {a.id for a in first} & {a.id for a in second}


@pytest.mark.asyncio
async def test_concurrent_workers_never_claim_the_same_artist(seeder, librarian):
    for i in range(10):
        await librarian.register_track(f"Song {i}", f"Artist {i}", [])

    batches = await asyncio.gather(*(seeder.claim_artists(3) for _ in range(5)))

    ids = [a.id for batch in batches for a in batch]
    assert len(ids) == 10
    assert len(set(ids)) == 10


@pytest.mark.asyncio
async def test_seeded_songs_become_curator_candidates(seeder, librarian, pg):
    # Alice liked Money, so Pink Floyd is a liked artist
    spotify_for_profiler = AsyncMock()
    spotify_for_profiler.search_track.return_value = {
        "id": "t-money",
        "name": "Money",
        "artists": ["Pink Floyd"],
        "artist_ids": ["pf"],
        "genres": ["progressive rock"],
    }
    profiler = Profiler(pg, spotify_for_profiler, librarian)
    play = await profiler.record_play(1, 99, "Money", "Pink Floyd", requested_by=ALICE)
    assert play is not None
    await profiler.log_event(play, [ALICE], "like")

    await seeder.seed_round()

    curator = Curator(pg)
    picks = set()
    for seed in range(30):
        pick = await curator.pick_next(10, [ALICE], rng=random.Random(seed))
        assert pick is not None
        picks.add(pick.title)
    # never-played songs by a liked artist are now pickable
    assert {"Time", "Wish You Were Here"} <= picks


@pytest.mark.asyncio
async def test_prepare_artist_then_similar_pick(seeder, librarian, pg):
    similar = await seeder.prepare_artist("pink floyd")

    assert similar is not None and similar.name == "Pink Floyd"
    assert await pg.fetch_val("SELECT count(*) FROM songs") == 3  # top tracks
    pick = await Curator(pg).pick_similar(
        10, [ALICE], similar.artist_id, similar.genre_ids, rng=random.Random(0)
    )
    assert pick is not None and pick.artist == "Pink Floyd"

    # asking again doesn't re-seed or duplicate
    again = await seeder.prepare_artist("PINK FLOYD")
    assert again is not None and again.artist_id == similar.artist_id
    assert await pg.fetch_val("SELECT count(*) FROM artists") == 1
