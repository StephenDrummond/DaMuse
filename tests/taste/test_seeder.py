from unittest.mock import AsyncMock

import pytest

from taste import seeder as seeder_module
from taste.seeder import ARTISTS_PER_ROUND, MARKET, SeedArtist, Seeder, SimilarArtist

PINK_FLOYD = {"id": "pf", "name": "Pink Floyd", "genres": ["rock", "prog"]}


@pytest.fixture
def spotify():
    spotify = AsyncMock()
    spotify.find_artist.return_value = PINK_FLOYD
    spotify.get_artist.return_value = PINK_FLOYD
    spotify.artist_top_tracks.return_value = [
        {"id": "t1", "name": "Money", "artist_ids": ["pf"]},
        {"id": "t2", "name": "Time", "artist_ids": ["pf", "guest"]},
        {"id": "t3", "name": "Their Hit", "artist_ids": ["other", "pf"]},  # feature
    ]
    return spotify


@pytest.fixture
def librarian():
    return AsyncMock()


@pytest.fixture
def seeder(db, spotify, librarian):
    db.fetch_val.side_effect = [3, 5]  # song count before / after
    return Seeder(db, spotify, librarian)


@pytest.mark.asyncio
async def test_seed_artist_registers_main_artist_tracks(seeder, spotify, librarian):
    added = await seeder.seed_artist(
        SeedArtist(id=1, name="Pink Floyd", spotify_id="pf")
    )

    assert added == 2
    spotify.get_artist.assert_awaited_once_with("pf")
    spotify.find_artist.assert_not_awaited()
    spotify.artist_top_tracks.assert_awaited_once_with("pf", MARKET)
    registered = [c.args[0] for c in librarian.register_track.await_args_list]
    assert registered == [
        "Money",
        "Time",
    ]  # the feature on another artist's song is skipped
    first = librarian.register_track.await_args_list[0]
    assert first.args == ("Money", "Pink Floyd", ["rock", "prog"])
    assert first.kwargs == {
        "spotify_track_id": "t1",
        "spotify_artist_id": "pf",
        "source": "top_tracks",
    }


@pytest.mark.asyncio
async def test_seed_artist_without_spotify_id_looks_up_and_stores_it(
    seeder, spotify, db
):
    await seeder.seed_artist(SeedArtist(id=1, name="Pink Floyd", spotify_id=None))

    spotify.find_artist.assert_awaited_once_with("Pink Floyd")
    store_id = db.execute.await_args
    assert "UPDATE artists SET spotify_id" in store_id.args[0]
    assert store_id.args[1:] == (1, "pf")


@pytest.mark.asyncio
async def test_seed_artist_keeps_our_artist_name(seeder, spotify, librarian):
    spotify.get_artist.return_value = {**PINK_FLOYD, "name": "PINK FLOYD"}

    await seeder.seed_artist(SeedArtist(id=1, name="Pink Floyd", spotify_id="pf"))

    # registering under Spotify's spelling would create a second artist row
    assert {c.args[1] for c in librarian.register_track.await_args_list} == {
        "Pink Floyd"
    }


@pytest.mark.asyncio
async def test_seed_artist_not_on_spotify(seeder, spotify, librarian):
    spotify.find_artist.return_value = None

    added = await seeder.seed_artist(SeedArtist(id=1, name="Nobody", spotify_id=None))

    assert added == 0
    spotify.artist_top_tracks.assert_not_awaited()
    librarian.register_track.assert_not_awaited()


@pytest.mark.asyncio
async def test_seed_round_unclaims_artist_on_failure(seeder, spotify, db):
    db.fetch.return_value = [{"id": 1, "name": "Pink Floyd", "spotify_id": "pf"}]
    spotify.get_artist.side_effect = RuntimeError("rate limited")

    assert await seeder.seed_round() == 1

    unclaim = db.execute.await_args
    assert "SET seeded_at = NULL" in unclaim.args[0]
    assert unclaim.args[1:] == (1,)


@pytest.mark.asyncio
async def test_run_forever_drains_backlog_quickly(seeder, monkeypatch):
    sleeps = []

    async def fake_sleep(seconds):
        sleeps.append(seconds)
        if len(sleeps) == 2:
            raise RuntimeError("stop")

    monkeypatch.setattr(seeder_module.asyncio, "sleep", fake_sleep)
    seeder.seed_round = AsyncMock(side_effect=[ARTISTS_PER_ROUND, 1])

    with pytest.raises(RuntimeError, match="stop"):
        await seeder.run_forever()

    # a full batch means more may be waiting: short pause; otherwise the long one
    assert sleeps == [
        seeder_module.BACKLOG_PAUSE_SECONDS,
        seeder_module.SEED_INTERVAL_SECONDS,
    ]


# --- prepare_artist (!switch <artist>) ----------------------------------------


@pytest.mark.asyncio
async def test_prepare_artist_registers_and_seeds_now(db, spotify, librarian):
    librarian.find_artist.return_value = None
    librarian.register_artist.return_value = (12, [3, 4])
    db.fetch_val.side_effect = [None, 0, 2]  # never seeded; song counts 0 -> 2
    seeder = Seeder(db, spotify, librarian)

    similar = await seeder.prepare_artist("pink floyd")

    assert similar == SimilarArtist(artist_id=12, name="Pink Floyd", genre_ids=[3, 4])
    librarian.register_artist.assert_awaited_once_with(
        "Pink Floyd", ["rock", "prog"], "pf"
    )
    spotify.artist_top_tracks.assert_awaited_once_with("pf", MARKET)
    spotify.get_artist.assert_not_awaited()  # reuses the lookup it already did
    assert "SET seeded_at = now()" in db.execute.await_args.args[0]


@pytest.mark.asyncio
async def test_prepare_artist_keeps_our_stored_name(db, spotify, librarian):
    librarian.find_artist.return_value = (12, "pink floyd")
    librarian.register_artist.return_value = (12, [3])
    db.fetch_val.side_effect = [True]  # seeded recently: no Spotify top tracks
    seeder = Seeder(db, spotify, librarian)

    similar = await seeder.prepare_artist("PINK FLOYD")

    assert similar is not None and similar.name == "pink floyd"
    assert librarian.register_artist.await_args.args[0] == "pink floyd"
    spotify.artist_top_tracks.assert_not_awaited()


@pytest.mark.asyncio
async def test_prepare_artist_unknown(db, spotify, librarian):
    spotify.find_artist.return_value = None

    assert await Seeder(db, spotify, librarian).prepare_artist("Nobody") is None
    librarian.register_artist.assert_not_awaited()
