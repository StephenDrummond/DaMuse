from discord.ext import commands


class General(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = bot.db

    @commands.command()
    async def hello(self, ctx):
        await ctx.send(f"Hello {ctx.author}! You are a member of {ctx.guild.name}")


async def setup(bot):
    await bot.add_cog(General(bot))
