
import aiohttp
import re
import time
import traceback
import logging

import discord
from discord.ext import commands
from utils.soup import YouTubeClient
from utils.patterns import rick_roll_pattern

logger = logging.getLogger('utils.testing')


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

        t0 = time.monotonic()
        matches = list(self.bot.url_pattern.finditer(ctx.message.content))
        _matches = set([f"<{match.group(0)}>" for match in matches])
        dt0 = (time.monotonic()-t0)*1000
        s = f"URL Results: ({dt0:.3}ms)\n" + "\n".join(_matches) + "\n"
        await ctx.send(str(s))

        t1 = time.monotonic()
        to_resolve = [match.group(0) for match in matches]
        resolved = await self.bot.resolve(*to_resolve)
        _resolved = set([f"<{url}>" for url in resolved])
        dt1 = (time.monotonic()-t1)*1000
        s = f"Resolved URLs: ({dt1:.3}ms)\n" + "\n".join(_resolved) + "\n"
        await ctx.send(str(s))

        t2 = time.monotonic()
        yt_matches = set()
        for url in resolved:
            match = self.bot.yt_pattern.fullmatch(url)
            if match:
                yt_matches.add(match.group(0))
        _yt_matches = [f"<{url}>" for url in yt_matches]
        dt2 = (time.monotonic()-t2)*1000
        s = f"YouTube URLs: ({dt2:.3}ms)\n" + "\n".join(yt_matches) + "\n"
        await ctx.send(s)

        t3 = time.monotonic()
        rick_rolls = dict()
        async with aiohttp.ClientSession() as session:
            for url in yt_matches:
                client = YouTubeClient(session)
                data = await client.get_data(url)
                rick_rolls[url] = data
        s = ""
        for url, data in rick_rolls.items():
            s += f"<{url}>\n"
            for name, item in data.items():
                match_or_no_match = "MATCH" if len(list(rick_roll_pattern.finditer(item.lower()))) > 0 else "NO MATCH"
                s += f"    {name}: {match_or_no_match}\n"
        dt3 = (time.monotonic()-t3)*1000
        dtnet = (time.monotonic()-t0)*1000
        s = f"Rick Rolls: ({dt3:.3}ms)\n" + s
        await ctx.send(s)
        await ctx.send(f"Total time: {dt0 + dt1 + dt2 + dt3:.3}ms | {dtnet:.3}ms")

    @commands.command()
    async def redis_set(self, ctx, url, is_rick_roll: bool):
        try:
            await self.bot.redis.url_set(url, is_rick_roll)
            await ctx.send("Done.")
        except Exception as e:
            traceback.print_exception(e.__class__, e, e.__traceback__)
            await ctx.send(f"{e.__class__}: {str(e)}")

    @commands.command()
    async def redis_get(self, ctx, url):
        try:
            is_rick_roll = await self.bot.redis.url_get(url)
            await ctx.send(str(is_rick_roll))
        except Exception as e:
            traceback.print_exception(e.__class__, e, e.__traceback__)
            await ctx.send(f"{e.__class__}: {str(e)}")

    @commands.command()
    async def process_rick_rolls(self, ctx):
        await self.bot.process_rick_rolls(ctx.message)


def setup(bot):
    bot.add_cog(Testing(bot))
