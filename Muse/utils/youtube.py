import yt_dlp

from music_state.queues import queues

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
    async def from_url(url, ctx, music_cog, stream=True):
        info = ytdl.extract_info(url, download=False)
        if "entries" in info:
            info = info["entries"][0]  # first result
        info = {
            "title": info["title"],
            "url": info["url"] if stream else ytdl.prepare_filename(info)
        }

        if not info:
            await ctx.send("Couldn't find anything.")
            return

        queues[ctx.guild.id].append(info)

        if ctx.voice_client and not ctx.voice_client.is_playing():
            await music_cog._play_next_song(ctx)
        else:
            await ctx.send(f"Queueing: **{info['title']}**")


