import discord
from discord.ext import commands

import datetime
import sys
import psutil


class Users(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def invite(self, ctx):
        """Add me to your server!"""
        await ctx.send(f"**You can invite me here: <{discord.utils.oauth_url(self.bot.user.id)}>**")

    @commands.command()
    async def about(self, ctx):
        """Some info about me!"""
        embed = discord.Embed(color=ctx.author.color)
        embed.set_author(name=str(self.bot.user), icon_url=self.bot.user.avatar_url)
        embed.add_field(name="Version", value=self.bot.version)
        embed.add_field(name="Library", value='discord.py')
        embed.add_field(name="OS", value={'linux': 'Ubuntu', 'win32': 'Windows'}[sys.platform])

        dt = datetime.datetime.now()-self.bot.started_at
        if dt.days >= 7:
            uptime = f"{(_w := dt.days//7)} week" + ('s' if _w > 1 else '')
        elif dt.days >= 1:
            uptime = f"{(_d := dt.days)} day" + ('s' if _d > 1 else '')
        elif dt.seconds > 3599:
            uptime = f"{(_h := dt.seconds//3600)} hour" + ('s' if _h > 1 else '')
        elif dt.seconds > 59:
            uptime = f"{(_m := dt.seconds//60)} minute" + ('s' if _m > 1 else '')
        else:
            uptime = f"{dt.seconds} seconds"

        embed.add_field(name="Uptime", value=uptime)
        memory = int(psutil.Process().memory_info().rss//10**6)
        embed.add_field(name="Memory", value=f"{memory} MB")
        embed.add_field(name="Servers", value=str(len(self.bot.guilds)))
        embed.add_field(name="Users", value=str(len(self.bot.users)))

        embed.add_field(name="Source", value='[github](https://github.com/nwunderly/rickroll-warning-system)')
        embed.add_field(name="Add me!", value='[invite](https://discordapp.com/oauth2/authorize?client_id=687454860907511881&scope=bot)')

        embed.set_footer(text=f'created by {", ".join(str(self.bot.get_user(owner)) for owner in [448250281097035777, 204414611578028034])}')
        embed.timestamp = self.bot.user.created_at
        await ctx.send(embed=embed)

    @commands.command()
    async def report(self, ctx, url, is_rick_roll: bool):
        """Report a rickroll that the bot failed to detect, or a normal URL that the bot thought was a rickroll."""
        channel = self.bot.get_channel(self.bot.logging_channels['reports'])
        await channel.send(f"⚠ **New report:**\n"
                           f"User: {ctx.author} (`{ctx.author.id}`)\n"
                           f"URL: `{url}`\n"
                           f"is_rick_roll: {is_rick_roll}")
        await ctx.send("Sent!")

    @commands.command()
    async def check(self, ctx, *urls):
        """Scans a URL and returns a detailed report of the results."""
        await ctx.send("Checking URL...")
        result = await self.bot.find_rick_rolls('\n'.join(urls))
        await ctx.send(result)


def setup(bot):
    bot.add_cog(Users(bot))
