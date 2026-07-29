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
    name VARCHAR NOT NULL UNIQUE
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
