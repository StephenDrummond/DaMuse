from discord.ext import commands
from utils.helpers import is_valid_url
from queues.manager import queues
import asyncio

class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def play(self, ctx, song_link: str = None):
        if ctx.author.voice:
            channel = ctx.author.voice.channel
            if not ctx.voice_client:
                await channel.connect()
                await ctx.send(f"Joined {channel.name}!")
        else:
            await ctx.send("You are not in a voice channel!")
            return

        if song_link is None:
            await ctx.send("Please provide a link to play!")
            return
        elif is_valid_url(song_link):
            guild_id = ctx.guild.id
            if guild_id not in queues:
                queues[guild_id] = []
            queues[guild_id].append(song_link)
            await ctx.send(f"Added to queue: {song_link}")
        else:
            await ctx.send("Invalid link!")

async def setup(bot):
    await bot.add_cog(Music(bot))