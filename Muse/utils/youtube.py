import yt_dlp
from music_state.queues import queues

# yt_dlp configuration for audio extraction
ytdl_format_options = {
    'format': 'bestaudio/best',  # Best audio quality
    'noplaylist': True,          # Only single track
    'quiet': True,               # Suppress output of errors in terminal
    'default_search': 'ytsearch', # Search if not a URL
    'extractor_args': {
        'youtube': {
            'player_client': ['default', '-tv_simply'],  # Optimize extraction
        },
    },
}

ytdl = yt_dlp.YoutubeDL(ytdl_format_options)


class YTDLSource:
    @staticmethod
    async def from_url(url, ctx, music_cog, stream=True):
        """
        Extract audio info from URL or search term,
        add it to the queue, and start playback if not playing.
        """
        info = ytdl.extract_info(url, download=False)
        if "entries" in info:
            info = info["entries"][0]  # Take first search result

        info = {
            "title": info["title"],  # Song title
            "url": info["url"] if stream else ytdl.prepare_filename(info)  # Stream URL or filename
        }

        if not info:
            await ctx.send("Couldn't find anything.")
            return

        queues[ctx.guild.id].append(info)  # Add to guild's queue

        # If nothing playing, start playback
        if ctx.voice_client and not ctx.voice_client.is_playing():
            await music_cog._play_next_song(ctx)
        else:
            await ctx.send(f"Queueing: **{info['title']}**")
