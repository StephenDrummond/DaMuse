import discord
from discord.ext import commands

from music_state.channel_members import channels_and_members, add_member, remove_member
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
            self.add_channel_members_to_memory(guild)

            # Store all members of the guild into the database
            await self.add_all_guild_members_to_db(guild)

    @staticmethod
    def add_channel_members_to_memory(guild: discord.Guild) -> None:
        """
        Scans all voice channels in the guild and adds connected members
        to in-memory tracking for quick reference.

        :param guild: The Discord Guild to scan.
        """
        for channel in guild.voice_channels:
            if channel.members:  # If the channel has members connected
                for member in channel.members:
                    add_member(
                        guild.id, channel.id, member.id
                    )  # Track member in memory
                # Debug print to show current state of tracked members
                print(channels_and_members)

    async def add_all_guild_members_to_db(self, guild: discord.Guild) -> None:
        """
        Ensures all members of the guild are stored in the database.
        Uses 'ON CONFLICT DO NOTHING' to avoid duplicate entries.

        :param guild: The Discord Guild whose members should be added.
        """
        async for member in guild.fetch_members(limit=None):
            await self.librarian.add_member_to_db(member.id)

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
        guild_id: int = member.guild.id

        # Case 1: Member joins a voice channel
        if before.channel is None and after.channel is not None:
            add_member(guild_id, after.channel.id, member.id)
            print(f"{member} joined {after.channel}")

        # Case 2: Member leaves a voice channel
        elif before.channel is not None and after.channel is None:
            remove_member(guild_id, before.channel.id, member.id)
            print(f"{member} left {before.channel}")

        # Case 3: Member moves between voice channels
        elif before.channel != after.channel:
            if before.channel:
                remove_member(guild_id, before.channel.id, member.id)
            if after.channel:
                add_member(guild_id, after.channel.id, member.id)
            print(f"{member} moved from {before.channel} to {after.channel}")

        # Debug: Print current in-memory state for tracking
        print(channels_and_members)

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
