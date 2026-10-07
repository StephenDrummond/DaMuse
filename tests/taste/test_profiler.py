from unittest.mock import AsyncMock, patch

import pytest

from taste.librarian import TrackIds
from taste.profiler import EVENT_SIGNALS, PlayRecord, Profiler, level_rate

TRACK = TrackIds(song_id=10, artist_id=20, genre_ids=[30, 31])


@pytest.fixture
def librarian():
    librarian = AsyncMock()
    librarian.register_track.return_value = TRACK
    librarian.get_track_ids.return_value = TRACK
    return librarian


@pytest.fixture
def spotify():
    return AsyncMock()


@pytest.fixture
def profiler(db, spotify, librarian):
    return Profiler(db, spotify, librarian)


SPOTIFY_INFO = {
    "id": "trk1",
    "name": "Money",
    "artists": ["Pink Floyd"],
    "artist_ids": ["art1"],
    "genres": ["rock"],
}


def test_lookup_key_normalizes():
    assert Profiler.lookup_key(" Money ", "Pink Floyd") == "pink floyd|money"
    assert Profiler.lookup_key("Money", None) == "|money"


# --- resolve_track ---------------------------------------------------------


@pytest.mark.asyncio
async def test_resolve_track_cache_hit_skips_spotify(spotify, profiler, db):
    db.fetch_row.return_value = {
        "song_id": 10,
        "artist_id": 20,
        "genre_ids": [30, 31],
        "fresh": True,
    }
    with patch.object(spotify, "search_track", new_callable=AsyncMock) as search:
        assert await profiler.resolve_track("Money", "Pink Floyd") == TRACK
        search.assert_not_awaited()


@pytest.mark.asyncio
async def test_resolve_track_recent_miss_skips_spotify(spotify, profiler, db):
    db.fetch_row.return_value = {
        "song_id": None,
        "artist_id": None,
        "genre_ids": [],
        "fresh": True,
    }
    with patch.object(spotify, "search_track", new_callable=AsyncMock) as search:
        assert await profiler.resolve_track("Nope", None) is None
        search.assert_not_awaited()


@pytest.mark.asyncio
async def test_resolve_track_stale_miss_retries_spotify(
    spotify, profiler, db, librarian
):
    db.fetch_row.return_value = {
        "song_id": None,
        "artist_id": None,
        "genre_ids": [],
        "fresh": False,
    }
    with patch.object(
        spotify, "search_track", new_callable=AsyncMock, return_value=SPOTIFY_INFO
    ):
        assert await profiler.resolve_track("Money", None) == TRACK


@pytest.mark.asyncio
async def test_resolve_track_registers_and_caches(spotify, profiler, db, librarian):
    db.fetch_row.return_value = None
    with patch.object(
        spotify, "search_track", new_callable=AsyncMock, return_value=SPOTIFY_INFO
    ) as search:
        assert await profiler.resolve_track("Money", "Pink Floyd") == TRACK

    search.assert_awaited_once_with("Money", "Pink Floyd")
    librarian.register_track.assert_awaited_once_with(
        "Money",
        "Pink Floyd",
        ["rock"],
        spotify_track_id="trk1",
        spotify_artist_id="art1",
    )
    cache_args = db.execute.await_args.args
    assert "track_lookups" in cache_args[0]
    assert cache_args[1:] == ("pink floyd|money", 10)


@pytest.mark.asyncio
async def test_resolve_track_retries_without_artist(spotify, profiler, db):
    db.fetch_row.return_value = None
    with patch.object(
        spotify,
        "search_track",
        new_callable=AsyncMock,
        side_effect=[None, SPOTIFY_INFO],
    ) as search:
        assert await profiler.resolve_track("Money", "PinkFloydVEVO") == TRACK

    assert search.await_args_list[1].args == ("Money",)


@pytest.mark.asyncio
async def test_resolve_track_caches_miss(spotify, profiler, db, librarian):
    db.fetch_row.return_value = None
    with patch.object(
        spotify, "search_track", new_callable=AsyncMock, return_value=None
    ):
        assert await profiler.resolve_track("Nope", None) is None

    librarian.register_track.assert_not_awaited()
    assert db.execute.await_args.args[1:] == ("|nope", None)


@pytest.mark.asyncio
async def test_resolve_track_spotify_error_not_cached(spotify, profiler, db):
    db.fetch_row.return_value = None
    with patch.object(
        spotify,
        "search_track",
        new_callable=AsyncMock,
        side_effect=RuntimeError("rate limited"),
    ):
        assert await profiler.resolve_track("Money", None) is None

    db.execute.assert_not_awaited()


# --- record_play -----------------------------------------------------------


@pytest.mark.asyncio
async def test_record_play_inserts_play(profiler, conn):
    profiler.resolve_track = AsyncMock(return_value=TRACK)
    conn.fetchval.return_value = 99

    play = await profiler.record_play(1, 2, "Money", "Pink Floyd", requested_by=5)

    assert play == PlayRecord(play_id=99, track=TRACK)
    assert conn.fetchval.await_args.args[1:] == (10, 1, 2, 5)
    # requester made to exist before the FK insert
    assert conn.execute.await_args.args[1] == [5]


@pytest.mark.asyncio
async def test_record_play_known_song_skips_lookup(profiler, librarian, conn):
    profiler.resolve_track = AsyncMock()
    conn.fetchval.return_value = 99

    play = await profiler.record_play(1, 2, "t", None, requested_by=None, song_id=10)

    assert play is not None
    profiler.resolve_track.assert_not_awaited()
    librarian.get_track_ids.assert_awaited_once_with(10)
    conn.execute.assert_not_awaited()  # no requester to ensure


@pytest.mark.asyncio
async def test_record_play_unidentified_returns_none(profiler, db):
    profiler.resolve_track = AsyncMock(return_value=None)

    assert await profiler.record_play(1, 2, "t", None, requested_by=5) is None
    db.transaction.assert_not_called()


# --- log_event -------------------------------------------------------------

PLAY = PlayRecord(
    play_id=99, track=TrackIds(song_id=10, artist_id=20, genre_ids=[31, 30, 31])
)


@pytest.mark.asyncio
async def test_log_event_writes_event_and_all_scores(profiler, conn):
    await profiler.log_event(PLAY, [3, 1, 3], "like")

    calls = conn.execute.await_args_list
    ensure, event, song, artist, genre = calls
    assert ensure.args[1] == [1, 3]  # users de-duped and sorted
    assert event.args[1:] == (99, [1, 3], "like")
    target, rate = EVENT_SIGNALS["like"]
    assert "song_user_likes" in song.args[0]
    assert song.args[1:] == ([1, 3], [10], rate, target)
    assert "artist_user_likes" in artist.args[0]
    assert artist.args[2] == [20]
    assert "genre_user_likes" in genre.args[0]
    assert genre.args[2] == [30, 31]  # genres de-duped and sorted


@pytest.mark.asyncio
async def test_log_event_skips_genres_when_none(profiler, conn):
    play = PlayRecord(play_id=1, track=TrackIds(song_id=1, artist_id=2, genre_ids=[]))

    await profiler.log_event(play, [1], "listen")

    tables = [call.args[0] for call in conn.execute.await_args_list]
    assert not any("genre_user_likes" in query for query in tables)


@pytest.mark.asyncio
async def test_log_event_no_users_is_noop(profiler, db):
    await profiler.log_event(PLAY, [], "listen")

    db.transaction.assert_not_called()


@pytest.mark.asyncio
async def test_log_event_unknown_type_raises(profiler):
    with pytest.raises(ValueError):
        await profiler.log_event(PLAY, [1], "love")


def test_event_signals_are_valid():
    for target, rate in EVENT_SIGNALS.values():
        assert target in (0.0, 1.0)
        assert 0 < rate <= 1
    # explicit feedback should move scores more than passive listening
    assert EVENT_SIGNALS["like"][1] > EVENT_SIGNALS["listen"][1]


@pytest.mark.asyncio
async def test_skip_barely_moves_artist_and_genre(profiler, conn):
    await profiler.log_event(PLAY, [1], "skip")

    _, _, song, artist, genre = conn.execute.await_args_list
    target, rate = EVENT_SIGNALS["skip"]
    assert song.args[3:] == (rate, target)  # the song takes the full penalty
    assert artist.args[3] == pytest.approx(rate / 3)
    assert genre.args[3] == pytest.approx(rate / 5)


@pytest.mark.parametrize("event", ["listen", "like", "dislike"])
def test_other_events_move_every_level_equally(event):
    _, rate = EVENT_SIGNALS[event]

    assert level_rate(event, "song") == level_rate(event, "artist") == rate
    assert level_rate(event, "genre") == rate


def test_skip_rates_are_ordered():
    # song > artist > genre: the more songs a level covers, the less one skip says
    assert level_rate("skip", "song") > level_rate("skip", "artist")
    assert level_rate("skip", "artist") > level_rate("skip", "genre") > 0
