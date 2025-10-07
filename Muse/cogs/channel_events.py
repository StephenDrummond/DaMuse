import discord
from discord.ext import commands

from music_state.channel_members import channels_and_members, add_member, remove_member


class ChannelEvents(commands.Cog):
    """
    Handles Discord voice channel events and user tracking.
    This cog:
    - Tracks which members are currently in voice channels (in memory).
    - Updates the database with all known guild members.
    - Listens for voice state changes (join/leave/move).
    """

    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        """
        Called once when the bot is ready and connected to Discord.
        - Initializes in-memory tracking of all current voice channel members.
        - Populates the database with all known guild members (to ensure consistency).
        """
        member_list: ([])  # (Unused — could be removed or used later if needed.)
        for guild in self.bot.guilds:
            # Step 1: Add all members currently in voice channels to in-memory tracking.
            self.add_channel_members_to_memory(guild)
            # Step 2: Ensure all guild members are recorded in the database.
            await self.add_all_guild_members_to_db(guild)

    @staticmethod
    def add_channel_members_to_memory(guild: discord.Guild):
        """
        Adds all members currently connected to voice channels to in-memory tracking.
        This is run once at startup to sync the bot’s memory with the live server state.
        """
        for channel in guild.voice_channels:
            if channel.members:
                for member in channel.members:
                    add_member(guild.id, channel.id, member.id)
                # Print the current state of tracked members for debugging.
                print(channels_and_members)

    async def add_all_guild_members_to_db(self, guild: discord.Guild):
        """
        Ensures every guild member is present in the database.
        Uses 'ON CONFLICT DO NOTHING' to avoid duplicate inserts.
        """
        async for member in guild.fetch_members(limit=None):
            async with self.bot.pool.acquire() as connection:
                await connection.execute("""
                    INSERT INTO users (discord_id)
                    VALUES ($1)
                    ON CONFLICT (discord_id) DO NOTHING
                """, member.id)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        """
        Triggered whenever a user's voice state changes (join/leave/move).
        Updates the in-memory list to reflect the new state.

        :param member: The Discord Member whose voice state changed.
        :param before: The previous VoiceState of the member.
        :param after: The new VoiceState of the member.
        """
        guild_id = member.guild.id

        # Case 1: User joins a voice channel
        if before.channel is None and after.channel is not None:
            add_member(guild_id, after.channel.id, member.id)
            print(f"{member} joined {after.channel}")

        # Case 2: User leaves a voice channel
        elif before.channel is not None and after.channel is None:
            remove_member(guild_id, before.channel.id, member.id)
            print(f"{member} left {before.channel}")

        # Case 3: User moves between voice channels
        elif before.channel != after.channel:
            if before.channel:
                remove_member(guild_id, before.channel.id, member.id)
            if after.channel:
                add_member(guild_id, after.channel.id, member.id)
            print(f"{member} moved from {before.channel} to {after.channel}")

        # Debug: print updated in-memory tracking state
        print(channels_and_members)


async def setup(bot):
    """
    Asynchronously adds this cog to the bot.
    Called when the extension is loaded.
    """
    await bot.add_cog(ChannelEvents(bot))
