import aiohttp
import logging
import yaml
import traceback
from bs4 import BeautifulSoup
from collections import defaultdict, namedtuple

import discord
from discord.ext import commands

# custom imports
from bot.astley import Astley
from utils.patterns import *
from confidential import authentication


logger = logging.getLogger("bot.rick")

RickRollData = namedtuple('RickRollData', ['check', 'extra'])
# check is name of check (redis, soup, comments, etc)
# extra is extra data (specific section for soup, percent of flagged comments, etc)


class Rick(Astley):
    """
    A bot that detects and warns you about possible Rick rolls.
    """
    def __init__(self):
        super().__init__(command_prefix="!!")
        self.version = '1.0.2'
        self.startup_cogs = ['cogs.testing', 'cogs.admin', 'cogs.users']
        self.url_pattern = url_pattern
        self.yt_pattern = yt_pattern
        self.rickroll_pattern = rickroll_pattern
        self.comment_pattern = comment_pattern
        self.base_url = "https://www.googleapis.com/youtube/v3/commentThreads?"
        self.session = aiohttp.ClientSession()
        self.comments_to_retrieve = 100

    async def on_message(self, message):
        if message.author == self.user:
            return
        if not message.guild:
            await self.process_private_messages(message)
        else:
            await self.process_commands(message)
            if not message.content.lower().startswith(f'{self.command_prefix}check') and not message.content.lower().startswith(f'{self.command_prefix}report'):
                result = await self.process_rick_rolls(message)

    async def process_private_messages(self, message):
        msg = f"Received private message from {message.author} ({message.author.id}) - {message.clean_content}"
        logger.info(msg)
        # await self.get_channel(0).send(msg)

    def get_urls(self, s):
        return [match.group(0) for match in self.url_pattern.finditer(s)]

    def is_youtube(self, url):
        return self.yt_pattern.fullmatch(url)

    @staticmethod
    def strip_url(url):
        url = url if isinstance(url, str) else url.human_repr()
        if url.startswith('http://'):
            url = url[7:]
        elif url.startswith('https://'):
            url = url[8:]
        return url

    async def _resolve(self, *urls):
        """Deprecated"""
        resolved = set()
        async with aiohttp.ClientSession() as session:
            for url in urls:
                try:
                    if not url.startswith('http'):
                        url = 'http://' + url
                    async with session.head(url, allow_redirects=True) as response:
                        resolved_url = response.url.human_repr()
                        resolved.add(resolved_url)
                except aiohttp.InvalidURL:
                    pass
        return resolved

    async def process_results(self, message, rick_rolls: dict):
        if len(rick_rolls) > 1:
            urls = '```'+'\n'.join(list(rick_rolls.keys()))+'```'
            await message.channel.send(f"**⚠ Detected Rickroll at {len(rick_rolls)} URLs:\n**{urls}")
        else:
            await message.channel.send(f"**⚠ Detected Rickroll at URL:\n**```{list(rick_rolls.keys())[0]}```")

    async def process_rick_rolls(self, message):
        """
        Calls find_rick_rolls, then processes results, sends a message if necessary and adds any rick rolls found to redis cache.
        Returns True or False depending on whether any rick rolls were found.
        :param message: discord Message object to be checked.
        :return: list of dicts, each with "is_rick_roll" and "extra" fields.
        """
        logger.debug(f"Checking message {message.id}.")
        rick_rolls = await self.find_rick_rolls(message.content)

        if rick_rolls:
            await self.process_results(message, rick_rolls)

        # write new rick rolls to Redis
        # todo: cache non-rick-rolls too
        for url, data in rick_rolls.items():
            if data.check != 'redis':
                url = self.strip_url(url)
                await self.redis.url_set(url, True, data.check, data.extra)

        return bool(rick_rolls)

    async def find_rick_rolls(self, content):
        """
        Runs rickroll checks on any string, abstracted from process_rick_rolls for debugging.
        Returns breakdown of all detected rickroll links.
        """
        rick_rolls = dict()  # key: url, value: name of first check that caught this url

        # URLs in message
        urls = self.get_urls(content)  # this will be a list
        original_urls = [url for url in urls]

        # remove duplicate URLs by stripping "http://" and passing through set()
        urls = set([self.strip_url(url) for url in urls])

        # check redis cache
        # redis will have them cached without the http:// part
        rick_rolls, urls = await self.check_redis(rick_rolls, urls)

        # handle redirects
        responses = await self.resolve(urls)  # returns list of Response objects

        # check redis again, this time for any new URLs found after redirect
        redirect_urls = [response.url.human_repr() for response in responses if response.url.human_repr() not in original_urls]
        rick_rolls, urls = await self.check_redis(rick_rolls, redirect_urls)

        # check for YouTube URLs
        # todo: non-youtube URLs should scrape and check for embedded YouTube video
        responses = self.filter_youtube(responses)

        # download YouTube pages and check with rick roll regex
        rick_rolls, urls = await self.check_youtube_html(rick_rolls, responses)

        # check comments for any YouTube URLs that haven't already been flagged
        rick_rolls = await self.check_comments(rick_rolls, urls)

        return rick_rolls

    async def check_redis(self, rick_rolls, urls):
        for url in list(urls):
            url = self.strip_url(url)
            redis = await self.redis.url_get(url)
            if not redis or not isinstance(redis, dict):  # not cached, will continue on to the next set of checks
                continue
            is_rick_roll = redis.get('is_rick_roll')
            if is_rick_roll is True:  # it's a cached rick roll
                rick_rolls[url] = RickRollData('redis', redis['detected_by'])  # makes note that this is a rick roll along with the check that found it
                urls.remove(url)  # no longer needs to be checked
            elif is_rick_roll is False:  # it's a cached non-rick-roll
                urls.remove(url)  # it's been confirmed false, no longer needs to be checked
            else:
                logger.error(f"Database error, invalid result for URL: {url}")
        return rick_rolls, urls

    async def resolve(self, urls):
        """
        Takes list of URL strings and returns list of Response objects with resolved URLs.
        """
        resolved = set()
        responses = list()  # list of response objects to be passed on to next part
        for url in list(urls):
            try:
                if not url.startswith('http'):
                    url = 'http://' + url
                response = await self.session.get(url)
                resolved_url = response.url.human_repr()
                if resolved_url not in resolved:
                    responses.append(response)  # same response is held open to be used again for downloading the page
                    resolved.add(resolved_url)
                else:  # it resolves to a duplicate URL
                    # await response.release()
                    response.close()
            except aiohttp.InvalidURL:
                pass
        return responses

    def filter_youtube(self, responses):
        """
        Removes non-youtube URLs from list of Response objects
        """
        for response in (list(responses) if responses else []):
            match = self.yt_pattern.fullmatch(response.url.human_repr())
            if not match:
                # await response.release()
                response.close()
                responses.remove(response)  # removes if not youtube, otherwise leaves it
        return responses

    async def check_youtube_html(self, rick_rolls, responses):
        """
        Uses web scraping to check YouTube page title, video title, and video description
        Returns updated rick roll data and URLs that tested negative (to be checked using YouTube API)
        """
        urls = list()

        for response in (list(responses) if responses else []):

            # PARTIAL READ IS CURRENTLY BROKEN - DO NOT USE
            # data = await response.content.read(10**6)  # reads up to 1 megabyte
            # html = data.decode()

            html = await response.read()

            soup = BeautifulSoup(html, features="html.parser")

            # check page title
            if len(list(rickroll_pattern.finditer(soup.head.title.text.lower()))) > 0:
                url = self.strip_url(response.url)
                rick_rolls[url] = RickRollData('soup', 'page-title')

            # check video title
            elif len(list(rickroll_pattern.finditer(soup.find(id='eow-title').text.lower()))) > 0:
                url = self.strip_url(response.url)
                rick_rolls[url] = RickRollData('soup', 'video-title')

            # check video description
            elif len(list(rickroll_pattern.finditer(soup.find(id='eow-description').text.lower()))) > 0:
                url = self.strip_url(response.url)
                rick_rolls[url] = RickRollData('soup', 'video-description')

            # check SME recommended video (youtube automatically adds this when it detects a song)
            elif len(list(rickroll_pattern.finditer(soup.find('ul', {'class': 'watch-extras-section'}).text.lower()))) > 0:
                url = self.strip_url(response.url.human_repr())
                rick_rolls[url] = RickRollData('soup', 'recommended')

            else:
                urls.append(response.url.human_repr())
        return rick_rolls, urls
                
    async def check_comments(self, rick_rolls, urls):
        """
        Uses YouTube API to pull up to 100 top comments and checks for clues using regex.
        """
        urls = [url if isinstance(url, str) else url.human_repr() for url in urls]
        for url in urls:
            comments = await self.get_comments(url)
            is_rick_roll, percent, count = self.parse_comments(comments)
            if is_rick_roll:
                rick_rolls[self.strip_url(url)] = RickRollData('comments', {'percent': percent, 'count': count})
        return rick_rolls
    
    async def get_comments(self, url):
        """
        Pulls video comments using HTTP request to YouTube API.
        """
        url = url if isinstance(url, str) else url.human_repr()
        async with self.session.get(f"{self.base_url}part=snippet&videoId={url[-11:]}&textFormat=plainText&maxResults={self.comments_to_retrieve}&key={authentication.YOUTUBE_API_KEY}") as response:
            json = await response.json()
            i = json.get('items')
            i = i if i else []
            return [str(item['snippet']) for item in i]

    def parse_comments(self, comments):
        """
        Runs regex search on list of comments and returns count/percent of matches.
        """
        count = 0
        for i in comments:
            m = len(list(comment_pattern.finditer(i.lower())))
            if m:
                count += 1
        try: percent = (count / len(comments)) * 100
        except ZeroDivisionError: percent = 0
        if percent > 15 or count > 5:
            return True, percent, count
        else:
            return False, percent, count

    async def setup(self):
        for cog in self.startup_cogs:
            try:
                self.load_extension(cog)
            except commands.ExtensionFailed as exception:
                traceback.print_exception(type(exception), exception, exception.__traceback__)

    async def cleanup(self):
        await self.session.close()



