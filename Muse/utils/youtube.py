import yt_dlp

ytdl_format_options = {
    'format': 'bestaudio/best',
    'noplaylist': True,
    'quiet': True,
    'default_search': 'ytsearch',
    'extractor_args': {
        'youtube': {
            'player_client': ['default', '-tv_simply'],
        },
    },
}

ytdl = yt_dlp.YoutubeDL(ytdl_format_options)

class YTDLSource:
    @staticmethod
    def from_url_sync(url, stream=False):
        """Blocking call — runs in a separate thread."""
        info = ytdl.extract_info(url, download=not stream)
        if "entries" in info:
            info = info["entries"][0]  # first result
        return {
            "title": info["title"],
            "url": info["url"] if stream else ytdl.prepare_filename(info),
            "duration": info.get("duration", 0),
            "webpage_url": info.get("webpage_url", url)
        }