from config import AudioSettings, DatabaseSettings, Settings


def test_defaults_from_empty_env():
    settings = Settings.from_env({})

    assert settings.discord_token is None
    assert settings.ffmpeg_path == "ffmpeg"
    assert settings.aws_region == "us-east-2"
    assert settings.database == DatabaseSettings()
    assert settings.audio == AudioSettings()


def test_reads_every_key():
    settings = Settings.from_env(
        {
            "DISCORD_TOKEN": "tok",
            "SPOTIFY_CLIENT_ID": "id",
            "SPOTIFY_CLIENT_SECRET": "secret",
            "AWS_REGION": "eu-west-1",
            "FFMPEG_PATH": "ffmpeg/bin/ffmpeg.exe",
            "DB_NAME": "muse",
            "DB_USER": "bot",
            "DB_HOST": "db.example",
            "DB_PORT": "6543",
            "DB_SSL_ROOT_CERT": "/certs/rds.pem",
            "DB_POOL_MIN_SIZE": "1",
            "DB_POOL_MAX_SIZE": "5",
            "DB_CONNECT_TIMEOUT": "30",
            "DATABASE_URL": "postgresql://localhost/test",
            "AUDIO_BUCKET": "bucket",
            "AUDIO_PREFIX": "a/",
            "AUDIO_WORKER_CONCURRENCY": "4",
            "AUDIO_MAX_DURATION": "600",
            "AUDIO_OPUS_BITRATE": "96k",
        }
    )

    assert (settings.discord_token, settings.spotify_client_id) == ("tok", "id")
    assert settings.ffmpeg_path == "ffmpeg/bin/ffmpeg.exe"
    assert settings.database == DatabaseSettings(
        name="muse",
        user="bot",
        host="db.example",
        port=6543,
        aws_region="eu-west-1",
        ssl_root_cert="/certs/rds.pem",
        pool_min_size=1,
        pool_max_size=5,
        connect_timeout=30,
        dsn="postgresql://localhost/test",
    )
    assert settings.audio == AudioSettings(
        bucket="bucket",
        prefix="a/",
        worker_concurrency=4,
        max_duration_seconds=600,
        opus_bitrate="96k",
    )


def test_empty_values_count_as_unset():
    settings = Settings.from_env({"AUDIO_BUCKET": "", "DB_PORT": ""})

    assert settings.audio.bucket is None
    assert settings.database.port == 5432
