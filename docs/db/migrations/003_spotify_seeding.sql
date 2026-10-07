-- 003: Spotify ids + seeding of artists' top tracks into the song registry.
-- Safe to re-run (IF NOT EXISTS everywhere).

BEGIN;

-- Spotify ids let the worker call per-artist endpoints (top tracks) without a
-- name search, and tell same-named artists apart. NULL until first known.
ALTER TABLE artists ADD COLUMN IF NOT EXISTS spotify_id VARCHAR;
-- When the worker last added this artist's top tracks (NULL = never).
ALTER TABLE artists ADD COLUMN IF NOT EXISTS seeded_at TIMESTAMPTZ;

ALTER TABLE songs ADD COLUMN IF NOT EXISTS spotify_id VARCHAR;
-- How the song got into the registry: 'played' (someone played it) or
-- 'top_tracks' (seeded from its artist's Spotify top tracks).
ALTER TABLE songs ADD COLUMN IF NOT EXISTS source VARCHAR NOT NULL DEFAULT 'played';

CREATE INDEX IF NOT EXISTS artists_seeded_at_idx ON artists (seeded_at NULLS FIRST);
CREATE INDEX IF NOT EXISTS songs_spotify_id_idx ON songs (spotify_id);

COMMIT;
