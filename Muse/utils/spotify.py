import os
from dotenv import load_dotenv
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials

load_dotenv()

SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")

# Authenticate with Client Credentials Flow
client_credentials_manager = SpotifyClientCredentials(
    client_id=SPOTIFY_CLIENT_ID,
    client_secret=SPOTIFY_CLIENT_SECRET
)

sp = spotipy.Spotify(client_credentials_manager=client_credentials_manager)


def get_spotify_track_info(spotify_url: str) -> dict:
    """
    Given a Spotify track URL, returns metadata about the track.
    Returns None if invalid or not found.
    """
    try:
        # Extract track ID from URL
        track_id = spotify_url.split("/")[-1].split("?")[0]
        track = sp.track(track_id)

        return {
            "name": track["name"],
            "artists": [artist["name"] for artist in track["artists"]],
            "album": track["album"]["name"],
            "duration_ms": track["duration_ms"],
            "url": track["external_urls"]["spotify"],
            "preview_url": track.get("preview_url"),
        }
    except Exception as e:
        print(f"[Spotify API Error] {e}")
        return None
