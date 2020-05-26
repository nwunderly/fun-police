import discord
from discord.ext import commands

import traceback
import logging

from confidential.authentication import YOUTUBE_API_KEY


logger = logging.getLogger('cogs.admin')


class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def load(self, ctx, *, cog):
        """Loads a cog."""
        try:
            self.bot.load_extension(cog)
        except commands.ExtensionError as e:
            await ctx.send(f'{e.__class__.__name__}: {e}')
        else:
            await ctx.send(f'Loaded {cog}.')

    @commands.command()
    async def unload(self, ctx, *, cog):
        """Unloads a cog."""
        try:
            self.bot.unload_extension(cog)
        except commands.ExtensionError as e:
            await ctx.send(f'{e.__class__.__name__}: {e}')
        else:
            await ctx.send(f'Unloaded {cog}.')

    @commands.command(name='reload')
    async def _reload(self, ctx, *, cog):
        """Reloads a cog."""
        try:
            self.bot.reload_extension(cog)
        except commands.ExtensionError as e:
            await ctx.send(f'{e.__class__.__name__}: {e}')
        else:
            await ctx.send(f'Reloaded {cog}.')

    @commands.command(name='set')
    async def redis_set(self, ctx, url, value):
        """Add or overwrite an item in redis cache. Evaluates value before writing."""
        value = eval(value)
        try:
            await self.bot.redis.set(url, value)
            await ctx.send("Done.")
        except Exception as e:
            logger.error(traceback.format_exception(e.__class__, e, e.__traceback__))
            await ctx.send(f"{e.__class__}: {str(e)}")

    @commands.command(name='get')
    async def redis_get(self, ctx, url):
        """Fetch an entry from redis cache."""
        try:
            is_rick_roll = await self.bot.redis.url_get(url)
            await ctx.send(str(is_rick_roll))
        except Exception as e:
            logger.error(traceback.format_exception(e.__class__, e, e.__traceback__))
            await ctx.send(f"{e.__class__}: {str(e)}")

    @commands.command(name='del')
    async def redis_del(self, ctx, *urls):
        """Remove an entry from redis cache."""
        try:
            await self.bot.redis.delete(urls)
            await ctx.send("Done.")
        except Exception as e:
            logger.error(traceback.format_exception(e.__class__, e, e.__traceback__))
            await ctx.send(f"{e.__class__}: {str(e)}")

    @commands.command()
    async def flag(self, ctx, url, is_rick_roll: bool = True):
        """Flag a URL as a rick roll (or not a rick roll)."""
        try:
            await self.bot.redis.url_set(url, is_rick_roll, 'manual', None)
            await ctx.send("Done.")
        except Exception as e:
            logger.error(traceback.format_exception(e.__class__, e, e.__traceback__))
            await ctx.send(f"{e.__class__}: {str(e)}")

    @commands.command()
    async def flag_playlist(self, ctx, url):
        """Flag every video in a YouTube playlist as a rick roll."""
        try:
            playlist_id = self.bot.yt_pattern.fullmatch(url).group(6)[6:]
            request_url = f"https://www.googleapis.com/youtube/v3/playlistItems?part=snippet&maxResults=50&playlistId={playlist_id}&key={YOUTUBE_API_KEY}"
            await ctx.send(playlist_id)
            async with self.bot.session.get(request_url) as response:
                json = await response.json()
                print(json)
            videos = json['items']
            async with ctx.trigger_typing():
                for video in videos:
                    await self.bot.redis.url_set(f"www.youtube.com/watch?v={video['snippet']['resourceId']['videoId']}", True, 'manual', None)
            await ctx.send(f"Added {len(videos)} to cache.")
        except Exception as e:
            logger.error(traceback.format_exception(e.__class__, e, e.__traceback__))
            await ctx.send(f"{e.__class__}: {str(e)}")



def setup(bot):
    bot.add_cog(Admin(bot))
