from yt_dlp import YoutubeDL

YDL_OPTIONS = {
    "format": "bestaudio/best",
    "noplaylist": True,
    "quiet": True,
}

def get_youtube_url(search: str) -> str:
    """
    Searches YouTube for a query and returns the direct audio URL.
    """
    with YoutubeDL(YDL_OPTIONS) as ydl:
        try:
            info = ydl.extract_info(f"ytsearch:{search}", download=False)["entries"][0]
            return info["url"]
        except Exception as e:
            print(f"[YouTube Error] {e}")
            return None
