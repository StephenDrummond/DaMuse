"""The write path (Librarian, Profiler, decay) and the read path (Curator)
against real Postgres: the SQL the unit tests only inspect as strings."""

import math
import random
from unittest.mock import AsyncMock

import pytest

from db.schedule_decay_preferences import DECAY_FUNCTION, DECAY_RATE
from taste.curator import Curator
from taste.librarian import Librarian, TrackIds
from taste.profiler import EVENT_SIGNALS, PlayRecord, Profiler

ALICE, BOB, CAROL = 1001, 1002, 1003


@pytest.fixture
def librarian(pg):
    return Librarian(pg)


@pytest.fixture
def spotify():
    spotify = AsyncMock()
    spotify.search_track.return_value = {
        "name": "Money",
        "artists": ["Pink Floyd"],
        "genres": ["progressive rock", "rock"],
    }
    return spotify


@pytest.fixture
def profiler(pg, spotify, librarian):
    return Profiler(pg, spotify, librarian)


async def score(pg, table, column, user_id, item_id):
    return await pg.fetch_val(
        f"SELECT preference_score FROM {table} WHERE user_id = $1 AND {column} = $2",
        user_id,
        item_id,
    )


def expected_after(*events, start=0.5):
    """Python mirror of the scoring formula, for checking the SQL."""
    value = start
    for event in events:
        target, rate = EVENT_SIGNALS[event]
        value = min(1.0, max(0.0, value + rate * (target - value)))
    return value


# --- Librarian -------------------------------------------------------------


@pytest.mark.asyncio
async def test_register_track_returns_same_ids_on_conflict(librarian, pg):
    first = await librarian.register_track("Money", "Pink Floyd", ["rock", "prog"])
    again = await librarian.register_track("Money", "Pink Floyd", ["prog", "rock"])

    assert again.song_id == first.song_id
    assert again.artist_id == first.artist_id
    assert sorted(again.genre_ids) == sorted(first.genre_ids)
    assert await pg.fetch_val("SELECT count(*) FROM songs") == 1
    assert await pg.fetch_val("SELECT count(*) FROM genres") == 2
    assert await pg.fetch_val("SELECT count(*) FROM artist_genres") == 2


@pytest.mark.asyncio
async def test_same_title_different_artist_is_a_different_song(librarian):
    a = await librarian.register_track("Hurt", "Nine Inch Nails", [])
    b = await librarian.register_track("Hurt", "Johnny Cash", [])

    assert a.song_id != b.song_id


@pytest.mark.asyncio
async def test_register_track_dedupes_genres(librarian, pg):
    ids = await librarian.register_track("Song", "Artist", ["rock", "rock"])

    assert len(ids.genre_ids) == 1


@pytest.mark.asyncio
async def test_get_track_ids(librarian):
    registered = await librarian.register_track("Money", "Pink Floyd", ["rock"])

    assert await librarian.get_track_ids(registered.song_id) == registered
    assert await librarian.get_track_ids(999_999) is None


@pytest.mark.asyncio
async def test_add_members_is_idempotent(librarian, pg):
    await librarian.add_members_to_db([(ALICE, "alice"), (BOB, "bob")])
    await librarian.add_members_to_db([(ALICE, "alice"), (CAROL, "carol")])
    await librarian.add_member_to_db(BOB, "bob")

    assert await pg.fetch_val("SELECT count(*) FROM users") == 3


# --- Profiler: plays, events, scoring --------------------------------------


@pytest.mark.asyncio
async def test_resolve_track_caches_hits_and_misses(profiler, spotify, pg):
    first = await profiler.resolve_track("Money", "Pink Floyd")
    second = await profiler.resolve_track("money ", "pink floyd")  # same key

    assert first is not None and second == first
    spotify.search_track.assert_awaited_once()  # second came from track_lookups

    spotify.search_track.return_value = None
    assert await profiler.resolve_track("Nope", None) is None
    assert await profiler.resolve_track("Nope", None) is None
    assert spotify.search_track.await_count == 2  # the miss is cached too
    assert (
        await pg.fetch_val("SELECT song_id FROM track_lookups WHERE query = '|nope'")
        is None
    )


@pytest.mark.asyncio
async def test_record_play_creates_users_and_play(profiler, pg):
    play = await profiler.record_play(1, 10, "Money", "Pink Floyd", requested_by=ALICE)

    assert play is not None
    row = await pg.fetch_row("SELECT * FROM plays WHERE id = $1", play.play_id)
    assert (
        row["song_id"],
        row["guild_id"],
        row["channel_id"],
        row["requested_by"],
    ) == (
        play.track.song_id,
        1,
        10,
        ALICE,
    )
    assert await pg.fetch_val("SELECT count(*) FROM users WHERE discord_id = $1", ALICE)


@pytest.mark.asyncio
async def test_curator_pick_play_has_no_requester(profiler, librarian, pg):
    track = await librarian.register_track("Money", "Pink Floyd", [])

    play = await profiler.record_play(
        1, 10, "ignored", None, requested_by=None, song_id=track.song_id
    )

    assert play is not None and play.track == track
    assert (
        await pg.fetch_val("SELECT requested_by FROM plays WHERE id = $1", play.play_id)
        is None
    )


@pytest.mark.asyncio
async def test_log_event_scores_every_level_for_every_user(profiler, pg):
    play = await profiler.record_play(1, 10, "Money", "Pink Floyd", requested_by=ALICE)
    assert play is not None

    await profiler.log_event(play, [ALICE, BOB, ALICE], "like")

    track = play.track
    for user in (ALICE, BOB):
        assert await score(
            pg, "song_user_likes", "song_id", user, track.song_id
        ) == pytest.approx(expected_after("like"))
        assert await score(
            pg, "artist_user_likes", "artist_id", user, track.artist_id
        ) == pytest.approx(expected_after("like"))
        for genre_id in track.genre_ids:
            assert await score(
                pg, "genre_user_likes", "genre_id", user, genre_id
            ) == pytest.approx(expected_after("like"))
    events = await pg.fetch(
        "SELECT user_id, event_type FROM play_events ORDER BY user_id"
    )
    assert [(e["user_id"], e["event_type"]) for e in events] == [
        (ALICE, "like"),
        (BOB, "like"),
    ]


@pytest.mark.asyncio
async def test_scores_follow_the_moving_average(profiler, pg):
    play = await profiler.record_play(1, 10, "Money", "Pink Floyd", requested_by=ALICE)
    assert play is not None
    sequence = ["listen", "like", "skip", "dislike", "listen"]

    for event in sequence:
        await profiler.log_event(play, [ALICE], event)

    assert await score(
        pg, "song_user_likes", "song_id", ALICE, play.track.song_id
    ) == pytest.approx(expected_after(*sequence))
    liked = await pg.fetch_val(
        "SELECT liked FROM song_user_likes WHERE user_id = $1", ALICE
    )
    assert liked is True  # the last event ("listen") was positive


@pytest.mark.asyncio
async def test_scores_stay_within_bounds(profiler, pg):
    play = await profiler.record_play(1, 10, "Money", "Pink Floyd", requested_by=ALICE)
    assert play is not None

    for _ in range(50):
        await profiler.log_event(play, [ALICE], "like")
    high = await score(pg, "song_user_likes", "song_id", ALICE, play.track.song_id)
    for _ in range(50):
        await profiler.log_event(play, [ALICE], "dislike")
    low = await score(pg, "song_user_likes", "song_id", ALICE, play.track.song_id)

    assert 0.99 < high <= 1.0
    assert 0.0 <= low < 0.01


@pytest.mark.asyncio
async def test_log_event_with_duplicate_genres(profiler, pg):
    play = await profiler.record_play(1, 10, "Money", "Pink Floyd", requested_by=ALICE)
    assert play is not None
    doubled = PlayRecord(
        play_id=play.play_id,
        track=TrackIds(
            song_id=play.track.song_id,
            artist_id=play.track.artist_id,
            genre_ids=play.track.genre_ids * 2,
        ),
    )

    # Postgres rejects an upsert that touches a row twice; this must not
    await profiler.log_event(doubled, [ALICE], "listen")


@pytest.mark.asyncio
async def test_log_event_is_atomic(profiler, pg):
    play = await profiler.record_play(1, 10, "Money", "Pink Floyd", requested_by=ALICE)
    assert play is not None
    broken = PlayRecord(
        play_id=play.play_id,
        track=TrackIds(song_id=play.track.song_id, artist_id=999_999, genre_ids=[]),
    )

    with pytest.raises(Exception):  # artist FK violation mid-transaction
        await profiler.log_event(broken, [ALICE], "like")

    # the event and the song score written before the failure were rolled back
    assert await pg.fetch_val("SELECT count(*) FROM play_events") == 0
    assert await pg.fetch_val("SELECT count(*) FROM song_user_likes") == 0


# --- Decay -----------------------------------------------------------------


@pytest.mark.asyncio
async def test_decay_moves_idle_scores_toward_neutral(profiler, pg):
    play = await profiler.record_play(1, 10, "Money", "Pink Floyd", requested_by=ALICE)
    assert play is not None
    await profiler.log_event(play, [ALICE], "like")
    await profiler.log_event(play, [BOB], "dislike")
    await pg.execute(DECAY_FUNCTION)
    before = {
        row["user_id"]: row["preference_score"]
        for row in await pg.fetch(
            "SELECT user_id, preference_score FROM song_user_likes"
        )
    }

    await pg.execute("SELECT decay_preferences()")
    for user, old in before.items():  # touched today: left alone
        assert await score(
            pg, "song_user_likes", "song_id", user, play.track.song_id
        ) == pytest.approx(old)

    await pg.execute("UPDATE song_user_likes SET liked_at = now() - interval '3 days'")
    await pg.execute("SELECT decay_preferences()")

    for user, old in before.items():
        new = await score(pg, "song_user_likes", "song_id", user, play.track.song_id)
        assert new == pytest.approx(0.5 + (old - 0.5) * math.exp(-DECAY_RATE))


# --- Curator ---------------------------------------------------------------


async def like(profiler, title, artist, genres, users, times=3, channel=10):
    profiler.spotify.search_track.return_value = {
        "name": title,
        "artists": [artist],
        "genres": genres,
    }
    play = await profiler.record_play(1, channel, title, artist, requested_by=users[0])
    for _ in range(times):
        await profiler.log_event(play, users, "like")
    return play


@pytest.mark.asyncio
async def test_group_scores_count_missing_members_as_neutral(profiler, pg):
    play = await like(profiler, "Money", "Pink Floyd", [], [ALICE], times=1)
    curator = Curator(pg)

    scores = await curator.group_scores([ALICE, BOB])

    alice = expected_after("like")
    assert scores["song"][play.track.song_id] == pytest.approx((alice + 0.5) / 2)


@pytest.mark.asyncio
async def test_curator_picks_what_the_room_likes(profiler, librarian, pg):
    await like(profiler, "Money", "Pink Floyd", ["rock"], [ALICE, BOB], channel=99)
    await librarian.register_track("Time", "Pink Floyd", ["rock"])  # same artist
    curator = Curator(pg)

    pick = await curator.pick_next(10, [ALICE, BOB], rng=random.Random(0))

    assert pick is not None
    assert pick.artist == "Pink Floyd"
    assert pick.score > 0.5


@pytest.mark.asyncio
async def test_curator_skips_songs_played_recently_in_the_channel(profiler, pg):
    await like(profiler, "Money", "Pink Floyd", [], [ALICE], channel=10)
    curator = Curator(pg)

    # the only liked song was just played in channel 10, but not in channel 20
    assert await curator.pick_next(10, [ALICE], rng=random.Random(0)) is None
    assert await curator.pick_next(20, [ALICE], rng=random.Random(0)) is not None


@pytest.mark.asyncio
async def test_curator_never_picks_a_disliked_song(profiler, librarian, pg):
    play = await like(profiler, "Money", "Pink Floyd", [], [ALICE], channel=99)
    for _ in range(10):
        await profiler.log_event(play, [ALICE], "dislike")

    assert await Curator(pg).pick_next(10, [ALICE], rng=random.Random(0)) is None


@pytest.mark.asyncio
async def test_curator_cold_start(pg):
    assert await Curator(pg).pick_next(10, [ALICE, BOB]) is None


@pytest.mark.asyncio
async def test_curator_excludes_songs_explicitly(profiler, pg):
    play = await like(profiler, "Money", "Pink Floyd", [], [ALICE], channel=99)
    curator = Curator(pg)

    # the song "still playing" in channel 10 has no plays row there yet
    assert await curator.pick_next(10, [ALICE], rng=random.Random(0)) is not None
    assert (
        await curator.pick_next(
            10,
            [ALICE],
            rng=random.Random(0),
            exclude_song_ids=[play.track.song_id],
        )
        is None
    )
