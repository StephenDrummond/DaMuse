-- 001: play history, Spotify lookup cache, and indexes for group curation.
-- Apply once to an existing database created from the original schema.sql
-- (schema.sql already includes everything below for fresh databases).

BEGIN;

-- One row per song the bot actually started playing in a voice channel.
CREATE TABLE plays (
    id BIGSERIAL PRIMARY KEY,
    song_id INT NOT NULL,
    guild_id BIGINT NOT NULL,
    channel_id BIGINT NOT NULL,
    -- NULL when the Curator picked the song for the room rather than a !play
    requested_by BIGINT,
    started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    FOREIGN KEY (song_id) REFERENCES songs(id) ON DELETE CASCADE,
    FOREIGN KEY (requested_by) REFERENCES users(discord_id) ON DELETE SET NULL
);

-- One row per listener reaction to a play. Everyone present when a song
-- finishes gets a 'listen'; 'skip' / 'like' / 'dislike' come from the member
-- who issued the command. Preference scores are derived from these events.
CREATE TABLE play_events (
    id BIGSERIAL PRIMARY KEY,
    play_id BIGINT NOT NULL,
    user_id BIGINT NOT NULL,
    event_type VARCHAR NOT NULL
        CHECK (event_type IN ('listen', 'skip', 'like', 'dislike')),
    occurred_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    FOREIGN KEY (play_id) REFERENCES plays(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(discord_id) ON DELETE CASCADE
);

-- Caches search query -> resolved song so repeat plays skip the Spotify API.
-- song_id NULL records a miss (Spotify had no match) so it isn't retried
-- on every play; misses are retried after a day.
CREATE TABLE track_lookups (
    query VARCHAR PRIMARY KEY,
    song_id INT,
    looked_up_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    FOREIGN KEY (song_id) REFERENCES songs(id) ON DELETE CASCADE
);

CREATE INDEX plays_channel_started_idx ON plays (channel_id, started_at DESC);
CREATE INDEX plays_song_idx ON plays (song_id);
CREATE INDEX play_events_play_idx ON play_events (play_id);
CREATE INDEX play_events_user_idx ON play_events (user_id, occurred_at DESC);

-- Curator candidate lookups: songs by artist, artists by genre.
CREATE INDEX songs_artist_idx ON songs (artist_id);
CREATE INDEX artist_genres_genre_idx ON artist_genres (genre_id);

COMMIT;
