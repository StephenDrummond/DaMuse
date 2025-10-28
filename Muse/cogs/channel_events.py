import asyncio

import discord
from discord.ext import commands

from utils.librarian import Librarian
from utils.observer import Observer


class ChannelEvents(commands.Cog):
    """
    Handles Discord voice channel events and user tracking.
    This cog:
    - Tracks which members are currently in voice channels (in memory).
    - Updates the database with all known guild members.
    - Listens for voice state changes (join/leave/move).
    """

    def __init__(self, bot: commands.Bot) -> None:
        self.bot: commands.Bot = bot
        self.db = bot.db  # type: ignore
        self.librarian: Librarian = Librarian(self.db)
        self.observer: Observer = Observer(self.db)

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        """
        Called when the bot is fully connected and ready.
        - Initializes in-memory tracking of all members currently in voice channels.
        - Ensures all members in the guilds are recorded in the database.
        """
        for guild in self.bot.guilds:
            # Sync current voice channel state to in-memory tracking
            await self.add_channel_members_to_memory(guild)

            # Store all members of the guild into the database
            await self.add_all_guild_members_to_db(guild)

    async def add_channel_members_to_memory(self, guild: discord.Guild) -> None:
        """
        Scans all voice channels in the guild and adds connected members
        to in-memory tracking for quick reference.

        :param guild: The Discord Guild to scan.
        """
        tasks = []
        for channel in guild.voice_channels:
            if channel.members:  # If the channel has members connected
                for member in channel.members:
                    tasks.append(self.observer.cache_prefs(channel.id, member.id))
        await asyncio.gather(*tasks)

    async def add_all_guild_members_to_db(self, guild: discord.Guild) -> None:
        """
        Ensures all members of the guild are stored in the database.
        Uses 'ON CONFLICT DO NOTHING' to avoid duplicate entries.

        :param guild: The Discord Guild whose members should be added.
        """
        async for member in guild.fetch_members(limit=None):
            await self.librarian.add_member_to_db(member.id, member.name)

    @commands.Cog.listener()
    async def on_voice_state_update(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ) -> None:
        """
        Called whenever a user's voice state changes (joins/leaves/moves channels).
        Updates the in-memory tracking state accordingly.

        :param member: The member whose voice state changed.
        :param before: Previous voice state before change.
        :param after: New voice state after change.
        """
        # Case 1: Member joins a voice channel
        if before.channel is None and after.channel is not None:
            await self.observer.cache_prefs(after.channel.id, member.id)

        # Case 2: Member leaves a voice channel
        elif before.channel is not None and after.channel is None:
            await self.observer.remove_user_prefs_from_cache(
                before.channel.id, member.id
            )

        # Case 3: Member moves between voice channels
        elif before.channel != after.channel:
            if before.channel:
                await self.observer.remove_user_prefs_from_cache(
                    before.channel.id, member.id
                )
            if after.channel:
                await self.observer.remove_user_prefs_from_cache(
                    after.channel.id, member.id
                )

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member) -> None:
        """
        Triggered when a new member joins any guild the bot is in.
        Adds them to the database to ensure tracking.

        :param member: The Discord Member who joined.
        """
        await self.librarian.add_member_to_db(member.id)


async def setup(bot: commands.Bot) -> None:
    """
    Adds the ChannelEvents cog to the bot.

    :param bot: The bot instance to add the cog to.
    """
    await bot.add_cog(ChannelEvents(bot))
