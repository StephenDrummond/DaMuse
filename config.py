"""All configuration, read from the environment (and .env) in one place.

Nothing else in the codebase calls os.getenv or load_dotenv: entry points
(main.py, worker.py, the decay script) call Settings.from_env() once and pass
the pieces down.
"""

import os
from dataclasses import dataclass
from typing import Mapping, Optional

from dotenv import load_dotenv


@dataclass(frozen=True)
class DatabaseSettings:
    name: Optional[str] = None
    user: Optional[str] = None
    host: Optional[str] = None
    port: int = 5432
    aws_region: str = "us-east-2"
    # RDS CA bundle path; when set, the server certificate is fully verified
    ssl_root_cert: Optional[str] = None
    # keep (processes x max size) under the cluster's connection limit
    pool_min_size: int = 3
    pool_max_size: int = 20
    # A plain connection string (local dev, tests). When set, it's used as-is
    # instead of IAM auth.
    dsn: Optional[str] = None


@dataclass(frozen=True)
class AudioSettings:
    bucket: Optional[str] = None  # unset: caching off, everything streams
    prefix: str = "audio/"
    # worker.py only
    worker_concurrency: int = 2
    max_duration_seconds: int = 1200
    opus_bitrate: str = "128k"


@dataclass(frozen=True)
class Settings:
    discord_token: Optional[str] = None
    spotify_client_id: Optional[str] = None
    spotify_client_secret: Optional[str] = None
    aws_region: str = "us-east-2"
    # ffmpeg executable; on Windows point it at ffmpeg/bin/ffmpeg.exe
    ffmpeg_path: str = "ffmpeg"
    database: DatabaseSettings = DatabaseSettings()
    audio: AudioSettings = AudioSettings()

    @classmethod
    def from_env(
        cls, env: Optional[Mapping[str, str]] = None, dotenv: bool = True
    ) -> "Settings":
        """Build settings from `env` (default: the process environment, after
        loading .env when `dotenv` is true)."""
        if env is None:
            if dotenv:
                load_dotenv()
            env = os.environ

        def get(key: str, default: Optional[str] = None) -> Optional[str]:
            value = env.get(key)
            return value if value not in (None, "") else default

        def get_int(key: str, default: int) -> int:
            value = get(key)
            return int(value) if value is not None else default

        region = get("AWS_REGION", "us-east-2") or "us-east-2"
        return cls(
            discord_token=get("DISCORD_TOKEN"),
            spotify_client_id=get("SPOTIFY_CLIENT_ID"),
            spotify_client_secret=get("SPOTIFY_CLIENT_SECRET"),
            aws_region=region,
            ffmpeg_path=get("FFMPEG_PATH", "ffmpeg") or "ffmpeg",
            database=DatabaseSettings(
                name=get("DB_NAME"),
                user=get("DB_USER"),
                host=get("DB_HOST"),
                port=get_int("DB_PORT", 5432),
                aws_region=region,
                ssl_root_cert=get("DB_SSL_ROOT_CERT"),
                pool_min_size=get_int("DB_POOL_MIN_SIZE", 3),
                pool_max_size=get_int("DB_POOL_MAX_SIZE", 20),
                dsn=get("DATABASE_URL"),
            ),
            audio=AudioSettings(
                bucket=get("AUDIO_BUCKET"),
                prefix=get("AUDIO_PREFIX", "audio/") or "audio/",
                worker_concurrency=get_int("AUDIO_WORKER_CONCURRENCY", 2),
                max_duration_seconds=get_int("AUDIO_MAX_DURATION", 1200),
                opus_bitrate=get("AUDIO_OPUS_BITRATE", "128k") or "128k",
            ),
        )
