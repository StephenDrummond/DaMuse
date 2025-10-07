import os
from typing import Optional, Dict, Any

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


def get_spotify_info(search_query: str) -> Optional[Dict[str, Any]]:
    """
    Search for an artist or track on Spotify and return relevant information.

    Tries to find an artist matching the search query first.
    If no artist is found, tries to find a track.
    Returns a dictionary containing either artist info (with top tracks)
    or track info (with genres).

    :param search_query: The search term (artist name or track name).
    :return: Dictionary of artist/track data, or None if no results found or error occurs.
    """
    try:
        # Search for artist matching the query
        artist_results: Dict[str, Any] = sp.search(q=f"artist:{search_query}", type="artist", limit=1)
        artists: list = artist_results.get("artists", {}).get("items", [])

        if artists:
            artist: Dict[str, Any] = artists[0]

            # Get top tracks for the artist
            top_tracks_data: Dict[str, Any] = sp.artist_top_tracks(artist["id"], country="US")
            top_tracks: list[str] = [track["name"] for track in top_tracks_data.get("tracks", [])[:5]]

            return {
                "type": "artist",
                "name": artist["name"],
                "genres": artist.get("genres", []),
                "followers": artist.get("followers", {}).get("total", 0),
                "url": artist["external_urls"]["spotify"],
                "uri": artist["uri"],
                "top_tracks": top_tracks
            }

        # If no artist found, search for track
        track_results: Dict[str, Any] = sp.search(q=f"track:{search_query}", type="track", limit=1)
        tracks: list = track_results.get("tracks", {}).get("items", [])

        if tracks:
            track: Dict[str, Any] = tracks[0]
            artist_id: str = track["artists"][0]["id"]

            # Get artist info for the track
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

        print("No results found.")
        return None

    except Exception as e:
        print(f"[Spotify API Error] {e}")
        return None


if __name__ == "__main__":
    # Prompt user for search query
    search_query: str = input("Enter an artist or song name: ")

    # Get Spotify information for query
    result: Optional[Dict[str, Any]] = get_spotify_info(search_query)

    # Display results
    if result:
        print(f"Result Type: {result['type']}")
        for k, v in result.items():
            if k != "type":
                print(f"{k}: {v}")
