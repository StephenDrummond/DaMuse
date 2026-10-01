import glob
import os
import subprocess
from dataclasses import dataclass
from typing import Any, Dict

import yt_dlp  # type: ignore

from api.youtube import parse_track_hint, ytdl_format_options

FFMPEG_PATH = os.getenv("FFMPEG_PATH", "ffmpeg")
# Longer sources (hour-long mixes, streams) aren't worth the storage.
MAX_DURATION_SECONDS = int(os.getenv("AUDIO_MAX_DURATION", "1200"))
# Only used when the source isn't Opus already. Discord plays Opus at 48 kHz;
# 128k is transparent for music and ~1 MB per minute in S3.
OPUS_BITRATE = os.getenv("AUDIO_OPUS_BITRATE", "128k")
FFMPEG_TIMEOUT_SECONDS = 600

# Prefer a native Opus stream (YouTube serves one for nearly every video):
# then encoding is a lossless container change, not a lossy re-encode.
DOWNLOAD_OPTIONS: Dict[str, Any] = {
    **ytdl_format_options,
    "format": "bestaudio[acodec=opus]/bestaudio/best",
    "no_warnings": True,
}


class PermanentEncodeError(Exception):
    """A job that will never succeed (too long, a live stream...): don't retry."""


@dataclass(frozen=True)
class EncodedAudio:
    path: str  # the Ogg Opus file
    metadata: Dict[str, Any]  # stored as S3 object metadata


def ffmpeg_command(src: str, dst: str, copy: bool) -> list[str]:
    """ffmpeg args turning `src` into an Ogg Opus file at `dst`: a stream
    copy when the source is already Opus, otherwise a libopus encode."""
    codec = (
        ["-c:a", "copy"]
        if copy
        else ["-c:a", "libopus", "-b:a", OPUS_BITRATE, "-ar", "48000", "-ac", "2"]
    )
    return [
        FFMPEG_PATH,
        "-nostdin",
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-i",
        src,
        "-map",
        "0:a:0",
        "-vn",
        "-map_metadata",
        "-1",
        *codec,
        "-f",
        "ogg",
        dst,
    ]


def check_cacheable(info: Dict[str, Any]) -> None:
    if info.get("is_live"):
        raise PermanentEncodeError("live streams can't be cached")
    duration = info.get("duration")
    if duration and duration > MAX_DURATION_SECONDS:
        raise PermanentEncodeError(
            f"{duration:.0f}s is over the {MAX_DURATION_SECONDS}s limit"
        )


def fetch_and_encode(source_url: str, workdir: str) -> EncodedAudio:
    """Blocking: download `source_url`'s best audio into `workdir` and convert
    it to Ogg Opus. Run it in a thread."""
    options = {**DOWNLOAD_OPTIONS, "outtmpl": os.path.join(workdir, "source.%(ext)s")}
    with yt_dlp.YoutubeDL(options) as ydl:
        # resolve first (process=False) so too-long/live sources are rejected
        # before downloading anything, then finish the same extraction
        raw = ydl.extract_info(source_url, download=False, process=False)
        check_cacheable(raw)
        info = ydl.process_ie_result(raw, download=True)

    downloads = glob.glob(os.path.join(workdir, "source.*"))
    if not downloads:
        raise RuntimeError(f"yt-dlp produced no file for {source_url}")

    dst = os.path.join(workdir, "audio.opus")
    command = ffmpeg_command(downloads[0], dst, copy=info.get("acodec") == "opus")
    result = subprocess.run(
        command, capture_output=True, text=True, timeout=FFMPEG_TIMEOUT_SECONDS
    )
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg failed: {result.stderr.strip()[-500:]}")

    artists = info.get("artists") or []
    hint_title, hint_artist = parse_track_hint(
        info.get("track") or info["title"],
        artists[0] if artists else info.get("artist"),
        info.get("channel"),
    )
    return EncodedAudio(
        path=dst,
        metadata={
            "title": info["title"],
            "hint-title": hint_title,
            "hint-artist": hint_artist,
            "source-url": info.get("webpage_url") or source_url,
            "duration": info.get("duration"),
        },
    )
