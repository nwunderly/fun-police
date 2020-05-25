import discord
from discord.ext import commands


class Users(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def invite(self, ctx):
        """Add me to your server!"""

    @commands.command()
    async def about(self, ctx):
        """Some info about me!"""

    @commands.command()
    async def report(self, ctx, url, is_rick_roll):
        """Report a rickroll that the bot failed to detect, or a normal URL that the bot thought was a rickroll."""

    @commands.command()
    async def check(self, ctx, url):
        """Scans a URL and returns a detailed report of the results."""


def setup(bot):
    bot.add_cog(Users(bot))
