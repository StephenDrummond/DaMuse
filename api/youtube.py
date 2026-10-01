import asyncio
import re
import time
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from typing import Dict, Any, Optional

import yt_dlp  # type: ignore

# yt_dlp configuration for audio extraction
ytdl_format_options: Dict[str, Any] = {
    "format": "bestaudio/best",  # Best audio quality
    "noplaylist": True,  # Only single track
    "quiet": True,  # Suppress yt-dlp output
    "default_search": "ytsearch",  # Search if not a URL
    "extractor_args": {
        "youtube": {
            "player_client": ["default", "-tv_simply"],  # Optimize extraction
        },
    },
}

# Initialize yt-dlp with the above options
ytdl = yt_dlp.YoutubeDL(ytdl_format_options)
# Same, but searches return just ids/titles without resolving any streams:
# enough to check the S3 audio cache, at a fraction of the cost.
ytdl_flat = yt_dlp.YoutubeDL({**ytdl_format_options, "extract_flat": "in_playlist"})

# yt_dlp extraction is blocking and CPU-heavy, so it runs in worker processes
executor = ProcessPoolExecutor()

# YouTube stream URLs expire after a few hours; anything resolved longer ago
# than this is re-resolved from its page URL right before playing.
STREAM_TTL_SECONDS = 30 * 60

_INFO_FIELDS = (
    "id",
    "extractor_key",
    "ie_key",  # flat search entries name the extractor here instead
    "title",
    "url",
    "webpage_url",
    "track",
    "artists",
    "artist",
    "channel",
    "duration",
)

_YOUTUBE_ID = re.compile(
    r"(?:youtube\.com/(?:watch\?(?:.*&)?v=|shorts/|embed/|live/)|youtu\.be/)"
    r"([A-Za-z0-9_-]{11})"
)


@dataclass(frozen=True)
class VideoRef:
    """Just enough to identify a video and check the audio cache."""

    audio_key: str  # "<extractor>/<id>", e.g. "youtube/dQw4w9WgXcQ"
    url: str  # page URL
    title: Optional[str] = None  # unknown when parsed straight from a URL
    channel: Optional[str] = None


@dataclass(frozen=True)
class VideoInfo:
    """A fully extracted video, including a (short-lived) direct stream URL."""

    audio_key: str
    url: str
    title: str
    stream_url: str
    hint_title: str
    hint_artist: Optional[str]
    duration: Optional[float]
    resolved_at: float  # time.monotonic() of the extraction

    @property
    def is_stale(self) -> bool:
        return time.monotonic() - self.resolved_at > STREAM_TTL_SECONDS


def audio_key(extractor: str, video_id: str) -> str:
    return f"{extractor.lower()}/{video_id}"


def youtube_video_id(text: str) -> Optional[str]:
    """The video id from a YouTube URL, or None if `text` isn't one."""
    match = _YOUTUBE_ID.search(text)
    return match.group(1) if match else None


def is_url(text: str) -> bool:
    return bool(re.match(r"https?://", text.strip()))


def run_ytdl(query: str) -> Optional[Dict[str, Any]]:
    """Runs in a worker process; returns only the fields we use so little
    has to be pickled back to the bot process."""
    info = ytdl.extract_info(query, download=False)
    if info and "entries" in info:  # a search: take the first hit
        entries = [entry for entry in info["entries"] if entry]
        info = entries[0] if entries else None
    if not info:
        return None
    return {field: info.get(field) for field in _INFO_FIELDS}


def run_ytdl_flat_search(query: str) -> Optional[Dict[str, Any]]:
    """Runs in a worker process: first search hit without stream resolution."""
    info = ytdl_flat.extract_info(f"ytsearch1:{query}", download=False)
    entries = [entry for entry in (info or {}).get("entries", []) if entry]
    if not entries:
        return None
    return {field: entries[0].get(field) for field in _INFO_FIELDS}


_NOISE = re.compile(
    r"\s*[(\[][^)\]]*\b(official|video|audio|lyrics?|visuali[sz]er|hd|hq|4k|mv)\b"
    r"[^)\]]*[)\]]",
    re.IGNORECASE,
)
_FEATURING = re.compile(r"\s*[(\[]?\b(ft|feat|featuring)\b\.?\s.*$", re.IGNORECASE)


def _clean(text: str) -> str:
    return _FEATURING.sub("", _NOISE.sub("", text)).strip()


def parse_track_hint(
    title: str,
    artist: Optional[str] = None,
    channel: Optional[str] = None,
) -> tuple[str, Optional[str]]:
    """Best-effort (song title, artist) from YouTube metadata, for Spotify.

    Prefers yt-dlp's music metadata when present, then the common
    "Artist - Title (Official Video)" title format, then auto-generated
    "Artist - Topic" channels.
    """
    if artist:
        return _clean(title), _clean(artist.split(",")[0])

    # split before stripping "ft. ..." -- it runs to the end of the string and
    # would swallow " - Title" when the credit is on the artist side
    denoised = _NOISE.sub("", title).strip()
    if " - " in denoised:
        artist_part, title_part = denoised.split(" - ", 1)
        return _clean(title_part), _clean(artist_part)
    cleaned = _clean(denoised)
    if channel and channel.endswith(" - Topic"):
        return cleaned, channel.removesuffix(" - Topic")
    return cleaned, None


async def find(query: str) -> Optional[VideoRef]:
    """Cheaply identify the video for a YouTube URL or a search term.

    Returns None for URLs from other sites (they need a full `extract` to
    learn their id) and for searches with no results.
    """
    video_id = youtube_video_id(query)
    if video_id is not None:
        return VideoRef(
            audio_key=audio_key("youtube", video_id),
            url=f"https://www.youtube.com/watch?v={video_id}",
        )
    if is_url(query):
        return None

    loop = asyncio.get_running_loop()
    hit = await loop.run_in_executor(executor, run_ytdl_flat_search, query)
    if not hit or not hit.get("id"):
        return None
    return VideoRef(
        audio_key=audio_key(
            hit.get("extractor_key") or hit.get("ie_key") or "youtube", hit["id"]
        ),
        url=hit.get("url") or f"https://www.youtube.com/watch?v={hit['id']}",
        title=hit.get("title"),
        channel=hit.get("channel"),
    )


async def extract(query: str) -> Optional[VideoInfo]:
    """Fully resolve a URL or search term, including a direct stream URL."""
    loop = asyncio.get_running_loop()
    info = await loop.run_in_executor(executor, run_ytdl, query)
    if not info or not info.get("url") or not info.get("id"):
        return None

    artists = info.get("artists") or []
    artist = artists[0] if artists else info.get("artist")
    hint_title, hint_artist = parse_track_hint(
        info.get("track") or info["title"], artist, info.get("channel")
    )
    return VideoInfo(
        audio_key=audio_key(info.get("extractor_key") or "youtube", info["id"]),
        url=info.get("webpage_url") or query,
        title=info["title"],
        stream_url=info["url"],
        hint_title=hint_title,
        hint_artist=hint_artist,
        duration=info.get("duration"),
        resolved_at=time.monotonic(),
    )
