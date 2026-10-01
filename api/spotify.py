import asyncio
import logging
import os
import re
from typing import Any, Dict, Optional, List

import spotipy  # type: ignore
from dotenv import load_dotenv
from spotipy.oauth2 import SpotifyClientCredentials  # type: ignore

# Load environment variables from .env file
load_dotenv()

# Spotify API credentials
SPOTIFY_CLIENT_ID: Optional[str] = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET: Optional[str] = os.getenv("SPOTIFY_CLIENT_SECRET")

# Authenticate with Spotify using client credentials flow
client_credentials_manager = SpotifyClientCredentials(
    client_id=SPOTIFY_CLIENT_ID, client_secret=SPOTIFY_CLIENT_SECRET
)
sp = spotipy.Spotify(client_credentials_manager=client_credentials_manager)

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


# spotipy is a blocking HTTP client, so every call goes through
# asyncio.to_thread to keep the Discord event loop responsive.


async def search_artist(search_query: str) -> Optional[Dict[str, Any]]:
    """Search for an artist and return relevant data."""
    artist_results: Dict[str, Any] = await asyncio.to_thread(
        sp.search, q=f"artist:{search_query}", type="artist", limit=1
    )
    artists: List[Dict[str, Any]] = artist_results.get("artists", {}).get("items", [])

    if not artists:
        return None

    artist: Dict[str, Any] = artists[0]
    top_tracks_data: Dict[str, Any] = await asyncio.to_thread(
        sp.artist_top_tracks, artist["id"], country="US"
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
    search_query: str, artist: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """Search for a track (optionally narrowed to an artist) and return relevant
    data. "genres" are the primary artist's, since Spotify tags artists, not
    tracks."""
    query = f"track:{search_query}"
    if artist:
        query += f" artist:{artist}"
    track_results: Dict[str, Any] = await asyncio.to_thread(
        sp.search, q=query, type="track", limit=1
    )
    tracks: List[Dict[str, Any]] = track_results.get("tracks", {}).get("items", [])

    if not tracks:
        return None

    track: Dict[str, Any] = tracks[0]
    artist_id: str = track["artists"][0]["id"]
    primary_artist: Dict[str, Any] = await asyncio.to_thread(sp.artist, artist_id)

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


_TRACK_URL = re.compile(r"open\.spotify\.com/(?:intl-[a-z-]+/)?track/([A-Za-z0-9]+)")


def spotify_track_id(text: str) -> Optional[str]:
    """The track id from a Spotify track link, or None if `text` isn't one."""
    match = _TRACK_URL.search(text)
    return match.group(1) if match else None


async def get_track_title_artist(track_id: str) -> Optional[tuple[str, str]]:
    """(title, primary artist) for a Spotify track id. Spotify doesn't serve
    full audio, so links are only used to find the song on YouTube."""
    track: Dict[str, Any] = await asyncio.to_thread(sp.track, track_id)
    if not track or not track.get("artists"):
        return None
    return track["name"], track["artists"][0]["name"]


async def get_spotify_info(search_query: str) -> Optional[Dict[str, Any]]:
    """Search Spotify for an artist or track and return data."""
    try:
        artist_info = await search_artist(search_query)
        if artist_info:
            return artist_info

        track_info = await search_track(search_query)
        if track_info:
            return track_info

        logger.exception("No results found.")
        return None
    except Exception as e:
        logger.exception(f"Error fetching Spotify data: {e}")
        return None
