
import aiohttp
import re

import discord
from discord.ext import commands

from utils.soup import YouTubeClient


rick_roll_pattern = re.compile(
    r"""(?:(?:never[^\n\w]*(?:gonna[^\n\w]*)?)?(?:give[^\n\w]*you[^\n\w]*up|let[^\n\w]*you[^\n\w]*down))|rick[^\n\w]*roll"""
)


class Testing(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def regex_url(self, ctx):
        """Tests URL detection regex on the whole command invocation message. Can detect multiple URLs."""
        matches = self.bot.url_pattern.finditer(ctx.message.content)
        matches = [f"<{match.group(0)}>" for match in matches]
        s = "\n".join(matches) if matches else None
        await ctx.send(str(s))

    @commands.command()
    async def regex_yt(self, ctx, url):
        """Tests YouTube URL regex on a url."""
        match = self.bot.yt_pattern.fullmatch(url)
        await ctx.send(str(bool(match)))

    @commands.command()
    async def redirect(self, ctx, url):
        """Returns the final URL that input URL resolves to, after redirects."""
        try:
            urls = await self.bot.resolve(url)
        except aiohttp.ClientConnectionError as e:
            await ctx.send(str(e))
            return
        await ctx.send(list(urls)[0])

    @commands.command()
    async def check(self, ctx, url):
        """Tests Rick Roll regex on a YouTube page's data and returns the result."""
        async with aiohttp.ClientSession() as session:
            client = YouTubeClient(session)
            data = await client.get_data(url)
        s = "Results:\n"
        for name, item in data.items():
            match_or_no_match = "MATCH" if len(list(rick_roll_pattern.finditer(item.lower()))) > 0 else "NO MATCH"
            s += f"{name}: {match_or_no_match}\n"
        await ctx.send(s)

    @commands.command()
    async def full_check(self, ctx):
        """URL regex -> redirect handling -> YouTube regex -> Page processing"""

        matches = list(self.bot.url_pattern.finditer(ctx.message.content))
        _matches = set([f"<{match.group(0)}>" for match in matches])
        s = "URL Results:\n" + "\n".join(_matches) + "\n"
        await ctx.send(str(s))

        to_resolve = [match.group(0) for match in matches]
        resolved = await self.bot.resolve(*to_resolve)
        _resolved = set([f"<{url}>" for url in resolved])
        s = "Resolved URLs:\n" + "\n".join(_resolved) + "\n"
        await ctx.send(str(s))

        yt_matches = set()
        for url in resolved:
            match = self.bot.yt_pattern.fullmatch(url)
            if match:
                yt_matches.add(match.group(0))
        _yt_matches = [f"<{url}>" for url in yt_matches]
        s = "YouTube URLs:\n" + "\n".join(yt_matches) + "\n"
        await ctx.send(s)

        rick_rolls = dict()
        async with aiohttp.ClientSession() as session:
            for url in yt_matches:
                client = YouTubeClient(session)
                data = await client.get_data(url)
                rick_rolls[url] = data
        s = "Rick Rolls:\n"
        for url, data in rick_rolls.items():
            s += f"<{url}>\n"
            for name, item in data.items():
                match_or_no_match = "MATCH" if len(list(rick_roll_pattern.finditer(item.lower()))) > 0 else "NO MATCH"
                s += f"    {name}: {match_or_no_match}\n"
        await ctx.send(s)


def setup(bot):
    bot.add_cog(Testing(bot))
