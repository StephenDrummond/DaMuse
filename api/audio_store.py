import asyncio
import logging
import os
from dataclasses import dataclass
from typing import Any, Optional
from urllib.parse import quote, unquote

import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

AUDIO_BUCKET = os.getenv("AUDIO_BUCKET")
AUDIO_PREFIX = os.getenv("AUDIO_PREFIX", "audio/")
AWS_REGION = os.getenv("AWS_REGION", "us-east-2")
# Signed playback URLs only need to outlive one song (ffmpeg reconnects use
# the same URL), but leave headroom for long tracks.
PRESIGNED_URL_TTL_SECONDS = 6 * 60 * 60

# Object metadata keys (S3 lowercases them and stores them as x-amz-meta-*).
_META_FIELDS = ("title", "hint-title", "hint-artist", "source-url", "duration")


@dataclass(frozen=True)
class CachedAudio:
    key: str  # full S3 object key
    title: str
    hint_title: str
    hint_artist: Optional[str]
    source_url: str
    duration: Optional[float]


class AudioStore:
    """S3-backed cache of songs pre-encoded as Ogg Opus.

    Objects live at "<prefix><audio key>.opus" (e.g. audio/youtube/<id>.opus)
    with the song's display/lookup metadata stored as object metadata, so a
    single HEAD request answers both "is it cached?" and "what is it?".

    IAM: the bot needs s3:GetObject and s3:ListBucket (without ListBucket, S3
    answers HEAD on a missing key with 403 instead of 404); the worker also
    needs s3:PutObject.
    """

    def __init__(self, bucket: str, prefix: str = "audio/", client: Any = None):
        self.bucket = bucket
        self.prefix = prefix
        self.client = client or boto3.client("s3", region_name=AWS_REGION)

    @classmethod
    def from_env(cls) -> Optional["AudioStore"]:
        """The configured store, or None (caching disabled, stream-only) when
        AUDIO_BUCKET isn't set."""
        if not AUDIO_BUCKET:
            logger.warning("AUDIO_BUCKET not set; audio caching disabled")
            return None
        return cls(AUDIO_BUCKET, AUDIO_PREFIX)

    def object_key(self, audio_key: str) -> str:
        return f"{self.prefix}{audio_key}.opus"

    async def lookup(self, audio_key: str) -> Optional[CachedAudio]:
        """HEAD the object: its metadata if cached, None if not.

        Errors other than "not found" are logged and reported as a miss, so
        an S3 hiccup degrades to streaming from YouTube instead of failing.
        """
        key = self.object_key(audio_key)
        try:
            head = await asyncio.to_thread(
                self.client.head_object, Bucket=self.bucket, Key=key
            )
        except ClientError as error:
            code = error.response.get("Error", {}).get("Code")
            if code not in ("404", "NoSuchKey", "NotFound"):
                logger.warning(
                    "S3 lookup for %s failed (%s); treating as miss", key, code
                )
            return None

        meta = {k: unquote(v) for k, v in head.get("Metadata", {}).items()}
        duration = meta.get("duration")
        return CachedAudio(
            key=key,
            title=meta.get("title") or audio_key,
            hint_title=meta.get("hint-title") or meta.get("title") or audio_key,
            hint_artist=meta.get("hint-artist") or None,
            source_url=meta.get("source-url") or "",
            duration=float(duration) if duration else None,
        )

    def playback_url(self, key: str) -> str:
        """A time-limited GET URL ffmpeg can read the object from. Signing is
        local (no request to S3), so this is cheap to call per song."""
        return self.client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket, "Key": key},
            ExpiresIn=PRESIGNED_URL_TTL_SECONDS,
        )

    def upload(self, path: str, audio_key: str, metadata: dict[str, Any]) -> str:
        """Blocking upload (worker only). Metadata values are URL-quoted since
        S3 metadata must be ASCII and titles often aren't."""
        key = self.object_key(audio_key)
        meta = {
            field: quote(str(metadata[field]))
            for field in _META_FIELDS
            if metadata.get(field) is not None
        }
        self.client.upload_file(
            path,
            self.bucket,
            key,
            ExtraArgs={"ContentType": "audio/ogg", "Metadata": meta},
        )
        return key
