import discord
from discord.ext import commands

from utils.librarian import Librarian


class ChannelEvents(commands.Cog):
    """
    Registers Discord members in the `users` table the first time they show up
    in a voice channel (the only place their listening history comes from).

    Who is in which voice channel is not mirrored anywhere: discord.py's voice
    state cache (`channel.members`) is the source of truth, read on demand.
    """

    def __init__(self, bot: commands.Bot) -> None:
        self.bot: commands.Bot = bot
        self.db = bot.db  # type: ignore
        self.librarian: Librarian = Librarian(self.db)
        # members already upserted by this process; skips a query per voice join
        self._registered: set[int] = set()

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        """
        Called when the bot is (re)connected: registers everyone currently in a
        voice channel, one batched round trip per guild.
        """
        for guild in self.bot.guilds:
            members = [
                member
                for channel in guild.voice_channels
                for member in channel.members
                if not member.bot and member.id not in self._registered
            ]
            await self.librarian.add_members_to_db(
                [(member.id, member.name) for member in members]
            )
            self._registered.update(member.id for member in members)

    @commands.Cog.listener()
    async def on_voice_state_update(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ) -> None:
        """
        Called whenever a user's voice state changes; registers members as they
        join voice.

        :param member: The member whose voice state changed.
        :param before: Previous voice state before change.
        :param after: New voice state after change.
        """
        if member.bot or after.channel is None:
            return
        if member.id not in self._registered:
            await self.librarian.add_member_to_db(member.id, member.name)
            self._registered.add(member.id)


async def setup(bot: commands.Bot) -> None:
    """
    Adds the ChannelEvents cog to the bot.

    :param bot: The bot instance to add the cog to.
    """
    await bot.add_cog(ChannelEvents(bot))
