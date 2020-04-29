
import aiohttp
import re

import discord
from discord.ext import commands

from utils.soup import YouTubeClient


class Testing(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def regex_url(self, ctx):
        matches = self.bot.url_pattern.finditer(ctx.message.content)
        matches = [f"<{match.group(0)}>" for match in matches]
        s = "\n".join(matches) if matches else None
        await ctx.send(str(s))

    @commands.command()
    async def regex_yt(self, ctx, url):
        match = self.bot.yt_pattern.fullmatch(url)
        await ctx.send(str(bool(match)))

    @commands.command()
    async def redirect(self, ctx, url):
        try:
            urls = await self.bot.resolve(url)
        except aiohttp.ClientConnectionError as e:
            await ctx.send(str(e))
            return
        await ctx.send(list(urls)[0])

    @commands.command()
    async def check(self, ctx, url):
        rick_roll_pattern = re.compile(r"""(never *gonna *give *you *up)|(rick *roll)""")
        async with aiohttp.ClientSession() as session:
            client = YouTubeClient(session)
            data = await client.get_data(url)
        s = "Results:\n"
        for name, item in data.items():
            match_or_no_match = "MATCH" if len(list(rick_roll_pattern.finditer(item.lower()))) > 0 else "NO MATCH"
            s += f"{name}: {match_or_no_match}\n"
        await ctx.send(s)


def setup(bot):
    bot.add_cog(Testing(bot))
