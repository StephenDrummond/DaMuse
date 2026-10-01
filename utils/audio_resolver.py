import logging
from dataclasses import dataclass
from typing import Optional

from api import youtube
from api.audio_store import AudioStore, CachedAudio
from api.spotify import get_track_title_artist, spotify_track_id
from api.youtube import VideoInfo
from utils.audio_jobs import AudioJobs

logger = logging.getLogger(__name__)

Hint = tuple[str, Optional[str]]  # (song title, artist) for the Spotify lookup


@dataclass(frozen=True)
class Track:
    audio_key: str  # "<extractor>/<id>": S3 key stem and audio_jobs id
    title: str  # display title
    source_url: str  # stable page URL, used to re-resolve an expired stream
    requested_by: Optional[int]  # None when the Curator picked it
    hint_title: str
    hint_artist: Optional[str]
    cached_key: Optional[str] = None  # S3 object key, if cached when resolved
    stream: Optional[VideoInfo] = None  # direct YouTube stream, if not cached


@dataclass(frozen=True)
class Playable:
    url: str
    from_cache: bool  # Ogg Opus from S3: passed through without re-encoding


class AudioResolver:
    """Finds audio for a request, preferring the S3 Opus cache.

    Cache hit: the song plays from S3, and YouTube is only searched (cheaply,
    no stream extraction). Miss: it streams straight from YouTube this time and
    an audio job is queued so worker.py caches it for next time. With no
    AudioStore configured, everything streams.
    """

    def __init__(self, store: Optional[AudioStore], jobs: AudioJobs):
        self.store = store
        self.jobs = jobs

    async def resolve(
        self, query: str, requested_by: Optional[int], hint: Optional[Hint] = None
    ) -> Optional[Track]:
        """Resolve a search term, YouTube/other URL, or Spotify track link."""
        spotify_id = spotify_track_id(query)
        if spotify_id is not None:
            found = await get_track_title_artist(spotify_id)
            if found is None:
                return None
            title, artist = found
            query = f"{artist} - {title}"
            hint = hint or (title, artist)

        ref = await youtube.find(query)
        if ref is not None:
            cached = await self._lookup(ref.audio_key)
            if cached is not None:
                return self._from_cache(ref.audio_key, cached, requested_by, hint)
            info = await youtube.extract(ref.url)
        elif youtube.is_url(query):
            # another site: only a full extraction reveals its id / cache key
            info = await youtube.extract(query)
            if info is not None:
                cached = await self._lookup(info.audio_key)
                if cached is not None:
                    return self._from_cache(info.audio_key, cached, requested_by, hint)
        else:
            return None  # search with no results

        if info is None:
            return None
        await self._enqueue(info)
        hint_title, hint_artist = hint or (info.hint_title, info.hint_artist)
        return Track(
            audio_key=info.audio_key,
            title=info.title,
            source_url=info.url,
            requested_by=requested_by,
            hint_title=hint_title,
            hint_artist=hint_artist,
            stream=info,
        )

    async def playable(self, track: Track) -> Playable:
        """The URL to hand ffmpeg right before playing `track`."""
        if self.store is not None and track.cached_key is not None:
            return Playable(self.store.playback_url(track.cached_key), from_cache=True)

        # the worker may have cached it while it sat in the queue
        cached = await self._lookup(track.audio_key)
        if self.store is not None and cached is not None:
            return Playable(self.store.playback_url(cached.key), from_cache=True)

        stream = track.stream
        if stream is None or stream.is_stale:
            stream = await youtube.extract(track.source_url)
            if stream is None:
                raise LookupError(f"Couldn't re-resolve {track.source_url}")
        return Playable(stream.stream_url, from_cache=False)

    async def _lookup(self, audio_key: str) -> Optional[CachedAudio]:
        if self.store is None:
            return None
        return await self.store.lookup(audio_key)

    async def _enqueue(self, info: VideoInfo) -> None:
        if self.store is None:
            return
        try:
            await self.jobs.enqueue(info.audio_key, info.url)
        except Exception:
            # caching is an optimization; never fail playback over it
            logger.exception("Couldn't queue %s for caching", info.audio_key)

    @staticmethod
    def _from_cache(
        audio_key: str,
        cached: CachedAudio,
        requested_by: Optional[int],
        hint: Optional[Hint],
    ) -> Track:
        hint_title, hint_artist = hint or (cached.hint_title, cached.hint_artist)
        return Track(
            audio_key=audio_key,
            title=cached.title,
            source_url=cached.source_url,
            requested_by=requested_by,
            hint_title=hint_title,
            hint_artist=hint_artist,
            cached_key=cached.key,
        )
