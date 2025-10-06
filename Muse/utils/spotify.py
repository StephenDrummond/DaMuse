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


def get_spotify_info(search_query: str) -> dict:
    """
    First tries to find an artist matching the search query.
    If not found, tries to find a track.
    Returns either artist info (with top 5 songs) or track info with genres.
    """
    try:
        # Search for artist first
        artist_results = sp.search(q=f"artist:{search_query}", type="artist", limit=1)
        artists = artist_results.get("artists", {}).get("items", [])

        if artists:
            artist = artists[0]

            # Get top tracks
            top_tracks_data = sp.artist_top_tracks(artist["id"], country="US")
            top_tracks = [track["name"] for track in top_tracks_data.get("tracks", [])[:5]]

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
        track_results = sp.search(q=f"track:{search_query}", type="track", limit=1)
        tracks = track_results.get("tracks", {}).get("items", [])

        if tracks:
            track = tracks[0]
            artist_id = track["artists"][0]["id"]
            artist = sp.artist(artist_id)

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
    search_query = input("Enter an artist or song name: ")
    result = get_spotify_info(search_query)

    if result:
        print(f"Result Type: {result['type']}")
        for k, v in result.items():
            if k != "type":
                print(f"{k}: {v}")
