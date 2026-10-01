from discord.ext import commands


class General(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.command()
    async def hello(self, ctx: commands.Context) -> None:
        guild_name = ctx.guild.name if ctx.guild else "no server"
        await ctx.send(f"Hello {ctx.author}! You are a member of {guild_name}")


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(General(bot))
