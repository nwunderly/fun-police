import discord
from discord.ext import commands

import traceback


class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def cog_check(self, ctx):
        return ctx.author.id in [448250281097035777, 204414611578028034]

    @commands.command(name='set')
    async def redis_set(self, ctx, url, is_rick_roll: bool):
        """Add or overwrite an item in redis cache."""
        try:
            await self.bot.redis.url_set(url, is_rick_roll, 'manual', None)
            await ctx.send("Done.")
        except Exception as e:
            traceback.print_exception(e.__class__, e, e.__traceback__)
            await ctx.send(f"{e.__class__}: {str(e)}")

    @commands.command(name='get')
    async def redis_get(self, ctx, url):
        """Fetch an entry from redis cache."""
        try:
            is_rick_roll = await self.bot.redis.url_get(url)
            await ctx.send(str(is_rick_roll))
        except Exception as e:
            traceback.print_exception(e.__class__, e, e.__traceback__)
            await ctx.send(f"{e.__class__}: {str(e)}")

    @commands.command(name='del')
    async def redis_del(self, ctx, *urls):
        """Remove an entry from redis cache."""
        try:
            await self.bot.redis.delete(urls)
            await ctx.send("Done.")
        except Exception as e:
            traceback.print_exception(e.__class__, e, e.__traceback__)
            await ctx.send(f"{e.__class__}: {str(e)}")

    @commands.command()
    async def flag(self, ctx, url):
        """Flag a URL as a rick roll."""

    @commands.command()
    async def flag_playlist(self, *urls):
        """Flag every video in a YouTube playlist as a rick roll."""
        pass




def setup(bot):
    bot.add_cog(Admin(bot))
