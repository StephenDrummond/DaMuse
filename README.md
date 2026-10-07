# DaMuse

DaMuse is a Discord music bot that plays for the whole voice channel instead of one person.
It remembers what each member likes at the song, artist and genre level, and when the queue
runs out it picks the next song based on the combined taste of everyone currently in the
channel. Someone joins and their taste starts counting. Someone leaves and it stops.

## Commands

| Command | What it does |
|---|---|
| `!play <song>` | Plays a song. Accepts a search term, a YouTube link or a Spotify track link. If something is already playing, the song is queued. |
| `!play` | With nothing after it, starts playing songs picked for the people in the channel. |
| `!skip` | Skips the current song. Counts as a mild dislike for whoever skipped. |
| `!switch` | Jumps to a random genre that has nothing in common with the current song, and keeps playing in that genre. |
| `!switch <artist>` | Jumps to a song by that artist or one in the same genres. Works for artists nobody has played yet. |
| `!stop` | Stops playback and clears the queue. |
| `!like` / `!dislike` | Tells the bot how you feel about the current song. These count much more than listening or skipping. |
| `!hello` | Health check. |

The bot leaves the voice channel after 3 minutes with nothing playing.

## How it works

### 1. Playing a song

When a song is requested, the bot first works out which YouTube video it is. A YouTube link
already contains the video id. A search term needs one quick YouTube search, and a Spotify
link is turned into an "artist - title" search, since Spotify does not provide full audio.

With the video id, the bot checks the S3 bucket for `audio/youtube/<id>.opus`.

- If the file is there, the bot downloads it from S3 and sends its audio packets straight to
  Discord. The files are already Ogg Opus, which is Discord's own voice format, so no ffmpeg
  process is started and nothing is decoded or re-encoded.
- If it is not there, the bot streams the song from YouTube through ffmpeg this one time, and
  adds a job to the `audio_jobs` table so the worker caches it for next time.

Songs are announced in the text channel the command came from. A requested song always plays
before the bot's own picks.

### 2. Remembering what people like

Every song that starts playing is looked up on Spotify to get its proper title, artist and the
artist's genres. Spotify tags artists rather than songs, so a song's genres are its artist's
genres. Lookups are cached in the `track_lookups` table so the same song is only looked up once.

Each member has a score between 0 and 1 for every song, artist and genre they have run into.
Anything they have never reacted to counts as 0.5 (neutral). Reactions move the scores:

| Event | When it happens | Song | Artist | Genres |
|---|---|---|---|---|
| listen | the song finished with you in the channel | 5% toward 1 | 5% toward 1 | 5% toward 1 |
| like | `!like` | 30% toward 1 | 30% toward 1 | 30% toward 1 |
| skip | `!skip`, for the person who skipped | 15% toward 0 | 5% toward 0 | 3% toward 0 |
| dislike | `!dislike` | 30% toward 0 | 30% toward 0 | 30% toward 0 |

"5% toward 1" means the score moves 5% of the remaining distance to 1, so a fresh 0.5 becomes
0.525. A skip mostly counts against the song itself, because skipping one song says little
about everything else by that artist or in that genre.

Every reaction is stored in `play_events` and the scores are updated in the same database
transaction, so the history and the scores never disagree. There is also an optional nightly
job that moves scores nobody has touched for a day 5% back toward 0.5, so old opinions fade
instead of lasting forever (see Database setup).

### 3. Picking the next song (the Curator)

When the queue is empty, the Curator (`taste/curator.py`) chooses a song for whoever is in the
voice channel:

1. **Combine the room's taste.** For every song, artist and genre, it averages the scores of
   everyone in the channel. A member with no opinion counts as 0.5, so one person's favorite
   moves the room less than the whole room agreeing.
2. **Find the song to follow.** This is the song playing now, or if nothing is playing, the
   last song played in the channel in the past 30 minutes.
3. **Gather candidates.** It looks for songs that are liked by the room, by an artist the room
   likes, or in a genre the room likes or the followed song has. Anything the room scores below
   the dislike threshold (0.35) is left out. Songs played in the channel in the last 2 hours,
   and the song playing now, are skipped.
4. **Score each candidate:** `0.5 x song score + 0.3 x artist score + 0.2 x average genre score`.
5. **Throw out the dislikes.** A candidate must score above 0.35 overall, and a song the room
   dislikes by name (its own song score below 0.35) is out even if its artist and genres score
   well.
6. **Stay close to what is playing.** If any remaining candidate shares a genre with the
   followed song, only those are considered. Otherwise all of them are.
7. **Pick one.** It takes the best 10 and picks one at random, weighted by how far each is above
   0.35. Better liked songs come up more often, but the bot does not play the same top song
   every time.

While a song is playing, the bot already prepares the pick after it, so there is no pause
between songs. If nothing can be picked, it says so in the text channel and starts the
inactivity timer.

`!switch` changes direction. It skips the current song (without counting it as a skip),
then picks a genre at random from the genres that share nothing with the current song and
have at least one song the room does not dislike. It picks a song in that genre the usual way,
and from then on picks follow the new genre. `!switch <artist>` looks the artist up on Spotify,
adds their top tracks if the bot does not have them yet, and picks a song by that artist or
another artist with the same genres. Spotify does not give this app "similar artist" data, so
similar means sharing genres. In both cases queued requests stay in the queue and play after
the new song.

The Curator can only pick songs that are in the `songs` table. Songs get there by being played,
or by the worker adding known artists' top tracks (next section).

### 4. The worker

`worker.py` runs next to the bot and does two jobs:

- **Caching audio.** It claims jobs from `audio_jobs`, downloads the audio with yt-dlp, converts
  it to Ogg Opus and uploads it to S3. YouTube almost always offers an Opus stream, in which
  case the conversion only changes the container and the audio is not re-encoded. Sources
  longer than 20 minutes and live streams are skipped. Failed jobs are retried up to 3 times,
  and a job a crashed worker left behind is picked up again after 15 minutes. The worker hears
  about new jobs through Postgres notifications and also checks every 30 seconds.
- **Adding songs (seeding).** Every 5 minutes it takes up to 5 artists that have never been
  seeded, or were last seeded more than 30 days ago, and adds each one's top 10 Spotify tracks
  to the `songs` table. Only tracks where that artist is the main artist are added, so features
  on other people's songs do not bring in new artists. Seeded songs are marked
  `source = 'top_tracks'`, and songs people played are marked `source = 'played'`.

Any number of workers can run at once. Each job and each artist is only ever handled by one of
them. Without `AUDIO_BUCKET` set, the worker only does the seeding.

## Project layout

| Path | Contents |
|---|---|
| `main.py` | Starts the bot. |
| `worker.py` | Starts the worker. |
| `app.py` | Builds all shared objects once (`Services`) and defines the bot class. |
| `config.py` | Reads all settings from `.env`. Nothing else reads environment variables. |
| `cogs/` | Discord commands and event listeners. |
| `playback/` | Per-server playback (`controller.py`), playing cached files without ffmpeg (`ogg_source.py`) and the inactivity timer. |
| `taste/` | Picking songs (`curator.py`), recording plays and scores (`profiler.py`), registering songs, artists and genres (`librarian.py`) and seeding (`seeder.py`). |
| `audio/` | Turning a request into something playable (`audio_resolver.py`), the caching job queue and the encoder the worker uses. |
| `clients/` | Spotify, YouTube (yt-dlp) and the S3 audio store. |
| `db/` | The connection pool, shared query helpers and one-off scripts (create tables, apply a migration, install the decay job). |
| `docs/db/` | `schema.sql`, the migrations, and the database diagram (`db.dbml`). |
| `tests/` | Unit tests, plus `tests/integration` which runs against a real Postgres. |

## Setup

### Requirements

- Python 3.13 and [Poetry](https://python-poetry.org/) 2.x
- ffmpeg. A Windows build is in `ffmpeg/`; on other systems install it normally.
- A Discord bot token with the **Server Members** and **Message Content** intents turned on.
- A Spotify app (client id and secret).
- An Aurora PostgreSQL cluster, and optionally an S3 bucket for the audio cache.

```powershell
poetry install
```

`poetry.toml` keeps the virtual environment in `.venv`, so IDEs and `.venv\Scripts\Activate.ps1`
find it as usual.

### Settings (`.env`)

| Key | Required | Notes |
|---|---|---|
| `DISCORD_TOKEN` | yes | |
| `SPOTIFY_CLIENT_ID`, `SPOTIFY_CLIENT_SECRET` | yes | |
| `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER` | yes | Aurora writer endpoint, usually port 5432 and user `postgres`. |
| `AWS_REGION` | yes | Defaults to `us-east-2`. |
| `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` | yes | Keys for the bot's IAM user, used for database login and S3. |
| `FFMPEG_PATH` | on Windows | `ffmpeg/bin/ffmpeg.exe`. Defaults to `ffmpeg` on the PATH. Start the bot from the project folder. |
| `AUDIO_BUCKET` | no | Turns on the S3 audio cache. Without it every song streams from YouTube. |
| `AUDIO_PREFIX` | no | Folder inside the bucket. Defaults to `audio/`. |
| `DB_SSL_ROOT_CERT` | no | Path to the [RDS certificate bundle](https://truststore.pki.rds.amazonaws.com/global/global-bundle.pem). Turns on certificate checking. |
| `DB_CONNECT_TIMEOUT` | no | Seconds to wait for a connection. Defaults to 60, long enough for a paused Serverless cluster to wake up. |
| `DB_POOL_MIN_SIZE`, `DB_POOL_MAX_SIZE` | no | Defaults 3 and 20. |
| `DATABASE_URL` | no | A normal connection string. When set, it is used instead of IAM login (local development). |
| `AUDIO_WORKER_CONCURRENCY` | no | Songs the worker caches at once. Defaults to 2. |
| `AUDIO_MAX_DURATION` | no | Longest song the worker will cache, in seconds. Defaults to 1200. |
| `AUDIO_OPUS_BITRATE` | no | Used only when a source is not already Opus. Defaults to `128k`. |

### AWS permissions

The database uses IAM login, so there is no database password. The bot generates a short-lived
login token from its AWS keys for every new connection. The IAM user needs:

- `rds-db:connect` on `arn:aws:rds-db:<region>:<account>:dbuser:<cluster resource id>/postgres`
- For the audio cache: `s3:GetObject` and `s3:PutObject` on `arn:aws:s3:::<bucket>/audio/*`, and
  `s3:ListBucket` on `arn:aws:s3:::<bucket>`. Without `ListBucket`, S3 reports a missing file as
  "access denied" instead of "not found" and the bot logs a warning for every uncached song.

The bucket can stay private. The bot plays files through short-lived signed links.

### Database setup

For a new, empty database, create all the tables:

```powershell
poetry run python -m db.apply_schema
```

For an existing database, apply each migration in `docs/db/migrations` that it does not have
yet, in order. The migrations are safe to run more than once.

```powershell
poetry run python -m db.migrate docs/db/migrations/003_spotify_seeding.sql
```

The nightly score decay is optional and needs the `pg_cron` extension. Add `pg_cron` to
`shared_preload_libraries` in the cluster's parameter group and reboot the writer instance,
then install the job (the script creates the extension, and tells you if `pg_cron` is not
loaded yet):

```powershell
poetry run python -m db.schedule_decay_preferences
```

## Running

Run the bot and the worker in two terminals from the project folder:

```powershell
poetry run python main.py
poetry run python worker.py
```

## Tests and checks

```powershell
poetry run pytest
poetry run mypy .
poetry run black .
poetry run flake8
```

The tests in `tests/integration` need a real, disposable Postgres database. They are skipped
unless `TEST_DATABASE_URL` is set, and they refuse to run against a database whose name does
not contain "test", because they delete everything in it:

```powershell
$env:TEST_DATABASE_URL = "postgresql://postgres:password@localhost:5432/damuse_test"
poetry run pytest
```

CI (`.github/workflows/ci.yml`) runs all of these on every push, with a Postgres 16 container
for the integration tests.

## Tuning

The main knobs are constants at the top of their files:

| Setting | File | Default | Meaning |
|---|---|---|---|
| `EVENT_SIGNALS` | `taste/profiler.py` | see the table above | How far each event moves a score. |
| `LEVEL_RATE_FACTORS` | `taste/profiler.py` | skip: artist 1/3, genre 1/5 | How much of an event reaches the artist and genres. |
| `WEIGHTS` | `taste/curator.py` | song 0.5, artist 0.3, genre 0.2 | How a candidate's score is put together. |
| `DISLIKE_THRESHOLD` | `taste/curator.py` | 0.35 | Below this, a song is never picked. |
| `RECENT_MINUTES` | `taste/curator.py` | 120 | How long before a song can repeat in a channel. |
| `CONTEXT_MINUTES` | `taste/curator.py` | 30 | How long the last song is followed after playback stops. |
| `TOP_K` | `taste/curator.py` | 10 | How many of the best candidates the random pick is made from. |
| `ARTISTS_PER_ROUND`, `RESEED_AFTER_DAYS` | `taste/seeder.py` | 5, 30 | Seeding batch size and how often an artist is refreshed. |
| `NEUTRAL_SCORE` | `db/client.py` | 0.5 | The score for anything nobody has reacted to. Not a cutoff. |

## Known limits

- The Curator only replays and reshuffles songs the bot knows about. Seeding adds more songs by
  known artists but does not discover new artists. Spotify's "related artists" and
  "recommendations" endpoints are not available to new apps, so discovering new artists would
  need another source such as Last.fm.
- Picks follow the genre of the previous song, so the room can stay in one genre for a while.
  A skip, a `!play` request or running out of matching songs changes it.
- A song's genres are its artist's genres.
- Typed searches and Curator picks still make one quick YouTube search to find the video id,
  even when the song is cached. Because of that, the same song can occasionally be cached twice
  from two different uploads.
