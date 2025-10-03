from discord.ext import commands
from music_state.channel_members import channels_and_members, add_member, remove_member


class ChannelEvents(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        for guild in self.bot.guilds:  # go to every server that the bot is on
            for channel in guild.voice_channels:  # iterate all voice channels
                if channel.members:  # if channel has members
                    for member in channel.members:
                        add_member(guild.id, channel.id, member.id)
                        print(channels_and_members)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        """ This event is called whenever a user's voice state changes. """
        guild_id = member.guild.id

        # User was not in a channel before, but now they are in one
        if before.channel is None and after.channel is not None:
            add_member(guild_id, after.channel.id, member.id)
            print(f"{member} joined {after.channel}")

        # User was in a channel before, but now they’re not in any channel
        elif before.channel is not None and after.channel is None:
            remove_member(guild_id, before.channel.id, member.id)
            print(f"{member} left {before.channel}")

        # User moved from one voice channel to another
        elif before.channel != after.channel:
            if before.channel:
                remove_member(guild_id, before.channel.id, member.id)
            if after.channel:
                add_member(guild_id, after.channel.id, member.id)
            print(f"{member} moved from {before.channel} to {after.channel}")

        print(channels_and_members)


async def setup(bot):
    """Load the ChannelEvents cog."""
    await bot.add_cog(ChannelEvents(bot))