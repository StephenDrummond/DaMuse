import asyncio
import logging
import re
from typing import Any, Dict, Optional, List

import spotipy  # type: ignore
from spotipy.oauth2 import SpotifyClientCredentials  # type: ignore

logger = logging.getLogger(__name__)

_TRACK_URL = re.compile(r"open\.spotify\.com/(?:intl-[a-z-]+/)?track/([A-Za-z0-9]+)")


def spotify_track_id(text: str) -> Optional[str]:
    """The track id from a Spotify track link, or None if `text` isn't one."""
    match = _TRACK_URL.search(text)
    return match.group(1) if match else None


class SpotifyClient:
    """Spotify Web API metadata lookups (client-credentials auth).

    spotipy is a blocking HTTP client, so every call goes through
    asyncio.to_thread to keep the Discord event loop responsive.
    """

    def __init__(
        self,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        sp: Any = None,
    ):
        """Pass `sp` to use a pre-built (or fake) spotipy client; otherwise one
        is built from the credentials."""
        self.sp = sp or spotipy.Spotify(
            client_credentials_manager=SpotifyClientCredentials(
                client_id=client_id, client_secret=client_secret
            )
        )

    async def search_artist(self, search_query: str) -> Optional[Dict[str, Any]]:
        """Search for an artist and return relevant data."""
        artist_results: Dict[str, Any] = await asyncio.to_thread(
            self.sp.search, q=f"artist:{search_query}", type="artist", limit=1
        )
        artists: List[Dict[str, Any]] = artist_results.get("artists", {}).get(
            "items", []
        )

        if not artists:
            return None

        artist: Dict[str, Any] = artists[0]
        top_tracks_data: Dict[str, Any] = await asyncio.to_thread(
            self.sp.artist_top_tracks, artist["id"], country="US"
        )
        top_tracks: List[str] = [
            track["name"] for track in top_tracks_data.get("tracks", [])[:5]
        ]

        return {
            "type": "artist",
            "name": artist["name"],
            "genres": artist.get("genres", []),
            "followers": artist.get("followers", {}).get("total", 0),
            "url": artist["external_urls"]["spotify"],
            "uri": artist["uri"],
            "top_tracks": top_tracks,
        }

    async def search_track(
        self, search_query: str, artist: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Search for a track (optionally narrowed to an artist) and return
        relevant data. "genres" are the primary artist's, since Spotify tags
        artists, not tracks."""
        query = f"track:{search_query}"
        if artist:
            query += f" artist:{artist}"
        track_results: Dict[str, Any] = await asyncio.to_thread(
            self.sp.search, q=query, type="track", limit=1
        )
        tracks: List[Dict[str, Any]] = track_results.get("tracks", {}).get("items", [])

        if not tracks:
            return None

        track: Dict[str, Any] = tracks[0]
        artist_id: str = track["artists"][0]["id"]
        primary_artist: Dict[str, Any] = await asyncio.to_thread(
            self.sp.artist, artist_id
        )

        return {
            "type": "track",
            "name": track["name"],
            "artists": [a["name"] for a in track["artists"]],
            "album": track["album"]["name"],
            "release_date": track["album"]["release_date"],
            "duration_ms": track["duration_ms"],
            "popularity": track["popularity"],
            "url": track["external_urls"]["spotify"],
            "uri": track["uri"],
            "preview_url": track.get("preview_url"),
            "genres": primary_artist.get("genres", []),
        }

    async def get_track_title_artist(self, track_id: str) -> Optional[tuple[str, str]]:
        """(title, primary artist) for a Spotify track id. Spotify doesn't serve
        full audio, so links are only used to find the song on YouTube."""
        track: Dict[str, Any] = await asyncio.to_thread(self.sp.track, track_id)
        if not track or not track.get("artists"):
            return None
        return track["name"], track["artists"][0]["name"]

    async def get_spotify_info(self, search_query: str) -> Optional[Dict[str, Any]]:
        """Search Spotify for an artist or track and return data."""
        try:
            artist_info = await self.search_artist(search_query)
            if artist_info:
                return artist_info

            track_info = await self.search_track(search_query)
            if track_info:
                return track_info

            logger.info("No Spotify results for %r", search_query)
            return None
        except Exception:
            logger.exception("Error fetching Spotify data for %r", search_query)
            return None
