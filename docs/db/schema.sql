-- Users table. Keyed directly on the Discord snowflake id (no separate
-- surrogate key) since every write path in the bot already identifies
-- users by their Discord id, not an internal id.
CREATE TABLE users (
    discord_id BIGINT PRIMARY KEY,
    username VARCHAR
);

-- Artists table
CREATE TABLE artists (
    id SERIAL PRIMARY KEY,
    name VARCHAR NOT NULL UNIQUE,
    spotify_id VARCHAR,
    -- when the worker last added this artist's top tracks (NULL = never)
    seeded_at TIMESTAMPTZ
);

-- Genres table
CREATE TABLE genres (
    id SERIAL PRIMARY KEY,
    name VARCHAR NOT NULL UNIQUE
);

-- Artist Genres join table
CREATE TABLE artist_genres (
    artist_id INT NOT NULL,
    genre_id INT NOT NULL,
    PRIMARY KEY (artist_id, genre_id),
    FOREIGN KEY (artist_id) REFERENCES artists(id) ON DELETE CASCADE,
    FOREIGN KEY (genre_id) REFERENCES genres(id) ON DELETE CASCADE
);

-- Songs table. Unique per (title, artist_id) rather than title alone,
-- since song titles collide across different artists/covers.
CREATE TABLE songs (
    id SERIAL PRIMARY KEY,
    title VARCHAR NOT NULL,
    artist_id INT NOT NULL,
    spotify_id VARCHAR,
    -- 'played' (someone played it) or 'top_tracks' (seeded from Spotify)
    source VARCHAR NOT NULL DEFAULT 'played',
    FOREIGN KEY (artist_id) REFERENCES artists(id) ON DELETE CASCADE,
    UNIQUE (title, artist_id)
);

-- Song User Likes table
CREATE TABLE song_user_likes (
    user_id BIGINT NOT NULL,
    song_id INT NOT NULL,
    liked BOOLEAN DEFAULT TRUE,
    liked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    preference_score FLOAT DEFAULT 0.5 CHECK (preference_score BETWEEN 0.0 AND 1.0),
    PRIMARY KEY (user_id, song_id),
    FOREIGN KEY (user_id) REFERENCES users(discord_id) ON DELETE CASCADE,
    FOREIGN KEY (song_id) REFERENCES songs(id) ON DELETE CASCADE
);

-- Genre User Likes table
CREATE TABLE genre_user_likes (
    user_id BIGINT NOT NULL,
    genre_id INT NOT NULL,
    liked BOOLEAN DEFAULT TRUE,
    liked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    preference_score FLOAT DEFAULT 0.5 CHECK (preference_score BETWEEN 0.0 AND 1.0),
    PRIMARY KEY (user_id, genre_id),
    FOREIGN KEY (user_id) REFERENCES users(discord_id) ON DELETE CASCADE,
    FOREIGN KEY (genre_id) REFERENCES genres(id) ON DELETE CASCADE
);

-- Artist User Likes table
CREATE TABLE artist_user_likes (
    user_id BIGINT NOT NULL,
    artist_id INT NOT NULL,
    liked BOOLEAN DEFAULT TRUE,
    liked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    preference_score FLOAT DEFAULT 0.5 CHECK (preference_score BETWEEN 0.0 AND 1.0),
    PRIMARY KEY (user_id, artist_id),
    FOREIGN KEY (user_id) REFERENCES users(discord_id) ON DELETE CASCADE,
    FOREIGN KEY (artist_id) REFERENCES artists(id) ON DELETE CASCADE
);

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

-- Audio cache work queue (see migrations/002_audio_jobs.sql)
CREATE TABLE audio_jobs (
    -- "<extractor>/<id>", e.g. "youtube/dQw4w9WgXcQ"; also the S3 key stem
    audio_key VARCHAR PRIMARY KEY,
    source_url VARCHAR NOT NULL,
    status VARCHAR NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'running', 'done', 'failed')),
    attempts INT NOT NULL DEFAULT 0,
    last_error TEXT,
    -- lease on a 'running' job; past it, the job is considered abandoned
    locked_until TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Workers scan only claimable rows, oldest first.
CREATE INDEX audio_jobs_claimable_idx ON audio_jobs (created_at)
    WHERE status IN ('pending', 'running');

-- Spotify seeding (see migrations/003_spotify_seeding.sql)
CREATE INDEX artists_seeded_at_idx ON artists (seeded_at NULLS FIRST);
CREATE INDEX songs_spotify_id_idx ON songs (spotify_id);
