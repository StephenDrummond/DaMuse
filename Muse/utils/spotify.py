import os
from typing import Any, Dict, Optional, List

import spotipy
from dotenv import load_dotenv
from spotipy.oauth2 import SpotifyClientCredentials

# Load environment variables from .env file
load_dotenv()

# Spotify API credentials
SPOTIFY_CLIENT_ID: Optional[str] = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET: Optional[str] = os.getenv("SPOTIFY_CLIENT_SECRET")

# Authenticate with Spotify using client credentials flow
client_credentials_manager = SpotifyClientCredentials(
    client_id=SPOTIFY_CLIENT_ID,
    client_secret=SPOTIFY_CLIENT_SECRET
)
sp = spotipy.Spotify(client_credentials_manager=client_credentials_manager)


def search_artist(search_query: str) -> Optional[Dict[str, Any]]:
    """Search for an artist and return relevant data."""
    artist_results: Dict[str, Any] = sp.search(q=f"artist:{search_query}", type="artist", limit=1)
    artists: List[Dict[str, Any]] = artist_results.get("artists", {}).get("items", [])

    if not artists:
        return None

    artist: Dict[str, Any] = artists[0]
    top_tracks_data: Dict[str, Any] = sp.artist_top_tracks(artist["id"], country="US")
    top_tracks: List[str] = [track["name"] for track in top_tracks_data.get("tracks", [])[:5]]

    return {
        "type": "artist",
        "name": artist["name"],
        "genres": artist.get("genres", []),
        "followers": artist.get("followers", {}).get("total", 0),
        "url": artist["external_urls"]["spotify"],
        "uri": artist["uri"],
        "top_tracks": top_tracks
    }


def search_track(search_query: str) -> Optional[Dict[str, Any]]:
    """Search for a track and return relevant data."""
    track_results: Dict[str, Any] = sp.search(q=f"track:{search_query}", type="track", limit=1)
    tracks: List[Dict[str, Any]] = track_results.get("tracks", {}).get("items", [])

    if not tracks:
        return None

    track: Dict[str, Any] = tracks[0]
    artist_id: str = track["artists"][0]["id"]
    artist: Dict[str, Any] = sp.artist(artist_id)

    return {
        "type": "track",
        "name": track["name"],
        "artists": [artist["name"] for artist in track["artists"]],
        "album": track["album"]["name"],
        "release_date": track["album"]["release_date"],
        "duration_ms": track["duration_ms"],
        "popularity": track["popularity"],
        "url": track["external_urls"]["spotify"],
        "uri": track["uri"],
        "preview_url": track.get("preview_url"),
        "genres": artist.get("genres", []),
    }


def get_spotify_info(search_query: str) -> Optional[Dict[str, Any]]:
    """Search Spotify for an artist or track and return data."""
    try:
        artist_info = search_artist(search_query)
        if artist_info:
            return artist_info

        track_info = search_track(search_query)
        if track_info:
            return track_info
        
        print("No results found.")
        return None
    except Exception as e:
        print(f"Error fetching Spotify data: {e}")
        return None


if __name__ == "__main__":
    info = get_spotify_info("Money Pink Floyd")
    print(info)
