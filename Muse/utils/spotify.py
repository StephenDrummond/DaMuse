import os

import spotipy
from dotenv import load_dotenv
from spotipy.oauth2 import SpotifyClientCredentials

load_dotenv()

SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")

# Authenticate
client_credentials_manager = SpotifyClientCredentials(
    client_id=SPOTIFY_CLIENT_ID,
    client_secret=SPOTIFY_CLIENT_SECRET
)
sp = spotipy.Spotify(client_credentials_manager=client_credentials_manager)


def get_spotify_track_info(search_query: str) -> dict:
    """
    Given a search query (e.g., "money pink floyd"), returns metadata about the top matching track.
    """
    try:
        results = sp.search(q=search_query, type="track", limit=1)
        tracks = results.get("tracks", {}).get("items", [])
        if not tracks:
            print("No results found.")
            return None

        track = tracks[0]
        artist_id = track["artists"][0]["id"]  # first artist
        artist = sp.artist(artist_id)

        return {
            "name": track["name"],
            "artists": [artist["name"] for artist in track["artists"]],
            "album": track["album"]["name"],
            "release_date": track["album"]["release_date"],
            "duration_ms": track["duration_ms"],
            "popularity": track["popularity"],
            "url": track["external_urls"]["spotify"],
            "uri": track["uri"],
            "preview_url": track.get("preview_url"),
            "genres": artist.get("genres", []),  # genres come from the artist
        }
    except Exception as e:
        print(f"[Spotify API Error] {e}")
        return None


track_info = get_spotify_track_info("we fell in love in october")
if track_info:
    for k, v in track_info.items():
        print(f"{k}: {v}")
