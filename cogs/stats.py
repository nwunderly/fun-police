import discord
import datetime
import aiohttp

from discord.ext import commands
from discord.ext import tasks

from confidential.authentication import WEBHOOKS


class DailyStats:
    def __init__(self):
        self.day = datetime.date.today()
        self.dumped = False

        self.messages_seen = 0
        self.urls_seen = 0
        self.youtube_urls_seen = 0
        self.youtube_urls_after_redirect = 0
        self.youtube_data_requests = 0
        self.youtube_comment_requests = 0
        self.rickrolls_detected = 0

    def dump(self):
        if self.dumped:
            raise Exception(f"({self.day}) ALREADY DUMPED.")
        data = str((
            self.messages_seen,
            self.urls_seen,
            self.youtube_urls_seen,
            self.youtube_urls_after_redirect,
            self.youtube_data_requests,
            self.youtube_comment_requests,
            self.rickrolls_detected
        ))
        with open('/home/rick/daily_stats.csv', 'a') as f:
            f.write("\n")
            f.write(','.join(data))
        self.dumped = True

    async def send(self):
        async with aiohttp.ClientSession() as session:
            hook = discord.Webhook.from_url(WEBHOOKS['stats'], adapter=discord.AsyncWebhookAdapter(session))
            e = discord.Embed(title=f"DAILY STATS FOR {self.day}", color=discord.Color.blurple())
            e.add_field(name="messages_seen", value=str(self.messages_seen))
            e.add_field(name="urls_seen", value=str(self.urls_seen))
            e.add_field(name="youtube_urls_seen", value=str(self.youtube_urls_seen))
            e.add_field(name="youtube_urls_after_redirect", value=str(self.youtube_urls_after_redirect))
            e.add_field(name="youtube_data_requests", value=str(self.youtube_data_requests))
            e.add_field(name="youtube_comment_requests", value=str(self.youtube_comment_requests))
            e.add_field(name="rickrolls_detected", value=str(self.rickrolls_detected))
            await hook.send(embed=e)


class Stats(commands.Cog):
    """
    Tracks stats for Fun Police.
    """
    def __init__(self, bot):
        self.today = datetime.date.today()
        self.stats = DailyStats()
        self.check_if_tomorrow.start()

    def cog_unload(self):
        self.check_if_tomorrow.cancel()

    def get_stats(self):
        return self.stats

    @tasks.loop(minutes=1)
    async def check_if_tomorrow(self):
        if self.today != datetime.date.today():
            self.stats.dump()
            await self.stats.send()
            self.stats = DailyStats()




