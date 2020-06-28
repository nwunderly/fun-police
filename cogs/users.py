import discord
from discord.ext import commands

import datetime
import psutil
import random

from utils.detector import RickRollDetector
from confidential import authentication


class Users(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def invite(self, ctx):
        """Add me to your server!"""
        await ctx.send(f"**You can invite me here: <{self.bot.properties.bot_url}>**")

    @commands.command()
    async def support(self, ctx):
        """Join the support server!"""
        await ctx.send(f"**Support server invite: <{self.bot.properties.server_url}>**")

    @commands.command()
    async def source(self, ctx):
        """My public github repository!"""
        await ctx.send(f"**My source code: <{self.bot.properties.github_url}>**")

    @commands.command()
    async def about(self, ctx):
        """Some info about me!"""
        embed = discord.Embed(color=ctx.author.color)
        embed.description = random.choice(f"{self.bot.description}", f"Check out our [website](https://www.youtube.com/watch?v=dQw4w9WgXcQ)!")
        embed.set_author(name=str(self.bot.user), icon_url=self.bot.user.avatar_url)
        embed.add_field(name="Version", value=self.bot.properties.version)
        embed.add_field(name="Library", value='discord.py')

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

        embed.add_field(name="Source", value=f'[github]({self.bot.properties.github_url})')
        embed.add_field(name="Add me!", value=f'[invite]({self.bot.properties.bot_url})')
        embed.add_field(name="Support server", value=f'[join]({self.bot.properties.server_url})')

        embed.set_footer(text=f'created by {" and ".join(str(self.bot.get_user(owner)) for owner in self.bot.properties.owner_ids)}')
        embed.timestamp = self.bot.user.created_at
        await ctx.send(embed=embed)

    @commands.command()
    async def report(self, ctx, url, is_rick_roll: bool):
        """Report a rickroll that the bot failed to detect, or a normal URL that the bot thought was a rickroll."""
        hook = discord.Webhook.from_url(authentication.WEBHOOKS['reports'], adapter=discord.AsyncWebhookAdapter(self.bot.session))
        await hook.send(f"⚠ **New report:**\n"
                        f"User: {ctx.author} (`{ctx.author.id}`)\n"
                        f"URL: `{url}`\n"
                        f"is_rick_roll: {is_rick_roll}")
        await ctx.send("Sent!")

    @commands.command()
    async def check(self, ctx, *urls):
        """Scans a URL and returns a detailed report of the results."""
        await ctx.send("Checking URL...")
        detector = RickRollDetector(self.bot, list(urls))
        result = await detector.find_rick_rolls()
        await ctx.send(result)

    @commands.command()
    async def vote(self, ctx):
        lists = "Please consider voting if you like our bot!\n" \
                "<https://top.gg/bot/687454860907511881>\n"\
                "<https://discord.bots.gg/bots/687454860907511881>\n"\
                "<https://discordbotlist.com/bots/fun-police>\n"\
                "<https://bots.ondiscord.xyz/bots/687454860907511881>"
        await ctx.send(lists)


def setup(bot):
    bot.add_cog(Users(bot))
