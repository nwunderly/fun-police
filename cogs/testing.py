
import aiohttp
import re
import time
import traceback
import logging
import copy
import boto3

import discord
from discord.ext import commands
from utils.soup import YouTubeClient
from utils.patterns import rickroll_pattern
from confidential.authentication import YOUTUBE_API_KEY

logger = logging.getLogger('cogs.testing')


class Testing(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.table = boto3.resource('dynamodb').Table('Rick')
        self.stats = {'correct': set(), 'total': set()}

    def cog_check(self, ctx):
        return ctx.author.id in [448250281097035777, 204414611578028034]

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
            responses = await self.bot.resolve([url])
            url = responses[0].url
        except aiohttp.ClientConnectionError as e:
            await ctx.send(str(e))
            return
        await ctx.send(url)

    @commands.command()
    async def redis_set(self, ctx, url, is_rick_roll: bool):
        try:
            await self.bot.redis.url_set(url, is_rick_roll, 'manual', None)
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
    async def redis_del(self, ctx, *urls):
        try:
            await self.bot.redis.delete(urls)
            await ctx.send("Done.")
        except Exception as e:
            traceback.print_exception(e.__class__, e, e.__traceback__)
            await ctx.send(f"{e.__class__}: {str(e)}")

    @commands.command()
    async def process_rick_rolls(self, ctx):
        await self.bot.process_rick_rolls(ctx.message)

    @commands.command(aliases=['a'])
    async def accuracy_test(self, ctx, url, is_rick_roll: bool = True):
        message = copy.copy(ctx.message)
        message.content = url

        guess = await self.bot.process_rick_rolls(message)

        if guess == is_rick_roll:
            self.stats['correct'].add(url)
            correct_guess = True
        else:
            correct_guess = False
        self.stats['total'].add(url)
        percent = str(len(self.stats['correct'])/len(self.stats['total'])*100) + '%' if len(self.stats['total']) != 0 else 'undefined'
        await ctx.send(f"Bot guessed {guess}, should be {is_rick_roll}.\n"
                       f"{'Correct' if correct_guess else 'Incorrect'} guess for {'' if is_rick_roll else 'non-'}rick-roll.\n"
                       f"{len(self.stats['correct'])}/{len(self.stats['total'])} guesses correct. ({percent})")

    @commands.command()
    async def stats(self, ctx):
        percent = str(len(self.stats['correct'])/len(self.stats['total'])*100) + '%' if len(self.stats['total']) != 0 else 'undefined'
        await ctx.send(f"{len(self.stats['correct'])}/{len(self.stats['total'])} guesses correct. ({percent})")

    @commands.command()
    async def check_playlists(self, ctx, *urls):
        rick_rolls = 0
        total = 0
        for url in urls:
            playlist_id = re.fullmatch(r"^((?:https?:)?//)?((?:www|m)\.)?((?:youtube\.com|youtu.be))(/(?:[\w\-]+\?v=|embed/|v/)?)([\w\-]+)(\S+)?$", url).group(6)[6:]
            request_url = f"https://www.googleapis.com/youtube/v3/playlistItems?part=snippet&maxResults=50&playlistId={playlist_id}&key={YOUTUBE_API_KEY}"
            await ctx.send(playlist_id)
            async with self.bot.session.get(request_url) as response:
                json = await response.json()
                print(json)
            videos = json['items']
            n = 0
            for i, video in enumerate(videos):
                total += 1
                video_url = f"https://www.youtube.com/watch?v={video['snippet']['resourceId']['videoId']}"
                message = copy.copy(ctx.message)
                message.content = video_url
                await ctx.send(f"Checking video {i}. (<{video_url}>)")
                try:
                    result = await self.bot.process_rick_rolls(message)
                except:
                    result = None
                if result:
                    n += 1
                    rick_rolls += 1
            await ctx.send(f"Found {n} rick rolls, playlist length {len(videos)}.")
        await ctx.send(f"Found {rick_rolls} rick rolls, total playlist length {total}.")


def setup(bot):
    bot.add_cog(Testing(bot))
