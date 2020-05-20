import aiohttp
import logging
import yaml
from bs4 import BeautifulSoup
from collections import defaultdict

# custom imports
from bot.backend import Astley
from utils.patterns import *


logger = logging.getLogger("bot.frontend")


class Rick(Astley):
    """
    A bot that detects and warns you about possible Rick rolls.
    """
    def __init__(self):
        super().__init__(command_prefix="!!")
        self.url_pattern = url_pattern
        self.yt_pattern = yt_pattern
        self.session = aiohttp.ClientSession()

    async def cleanup(self):
        await self.session.close()

    async def on_message(self, message):
        if message.author == self.user:
            return
        if not message.guild:
            await self.process_private_messages(message)
        else:
            await self.process_commands(message)
            # await self.process_rick_rolls(message) todo: add this back

    async def process_private_messages(self, message):
        msg = f"Received private message from {message.author} ({message.author.id}) - {message.clean_content}"
        logger.info(msg)
        await self.get_channel(0).send(msg)

    def get_urls(self, s):
        return [match.group(0) for match in self.url_pattern.finditer(s)]

    def is_youtube(self, url):
        return self.yt_pattern.fullmatch(url)

    @staticmethod
    def strip_url(url):
        return url.replace('http://', '').replace('https://', '')

    async def resolve(self, *urls):
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

    async def process_rick_rolls(self, message):
        logger.debug(f"Checking message {message.id}.")
        rick_rolls = dict()  # key: url, value: name of first check that caught this url

        # URLs in message
        urls = self.get_urls(message.content)  # this will be a list

        # remove duplicate URLs by stripping "http://" and passing through set()
        urls = set([url.replace('http://', '').replace('https://', '') for url in urls])

        # check redis cache
        # redis will have them cached without the http:// part
        for url in list(urls):
            url = self.strip_url(url)
            redis = await self.redis.url_get(url)
            if redis is True:  # it's a cached rick roll
                rick_rolls[url] = 'redis'  # makes note that this is a rick roll along with the check that found it
                urls.remove(url)  # no longer needs to be checked
            elif redis is False:  # it's a cached non-rick-roll
                urls.remove(url)  # it's been confirmed false, no longer needs to be checked
            elif redis is None:  # not cached, will continue on to the next set of checks
                continue
            else:
                logger.error(f"Database error, invalid result for URL: {url}")

        # handle redirects
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

        # check for YouTube URLs
        # todo: non-youtube URLs should scrape and check for embedded YouTube video
        for response in list(responses):
            match = self.yt_pattern.fullmatch(response.url.human_repr())
            if not match:
                # await response.release()
                response.close()
                responses.remove(response)  # removes if not youtube, otherwise leaves it

        # download YouTube pages and check with rick roll regex
        for response in responses:

            # PARTIAL READ IS CURRENTLY BROKEN - DO NOT USE
            # data = await response.content.read(10**6)  # reads up to 1 megabyte
            # html = data.decode()

            html = await response.read()

            soup = BeautifulSoup(html, features="html.parser")

            # check page title
            if len(list(rick_roll_pattern.finditer(soup.head.title.text.lower()))) > 0:
                rick_rolls[response.url] = 'soup-pagetitle'

            # check video title
            elif len(list(rick_roll_pattern.finditer(soup.find(id='eow-title').text))) > 0:
                rick_rolls[response.url] = 'soup-title'

            # check video description
            elif len(list(rick_roll_pattern.finditer(soup.find(id='eow-description').text))) > 0:
                rick_rolls[response.url] = 'soup-description'

        if rick_rolls:
            await message.channel.send(str(rick_rolls))
        else:
            # todo: remove this when putting it into on_message
            await message.channel.send("No rick rolls detected.")

        # write new rick rolls to Redis
        # todo: cache non-rick-rolls too
        for url, check_name in rick_rolls.items():
            if check_name != 'redis':
                await self.redis.url_set(url, True, check_name)

    async def setup(self):
        self.load_extension('utils.testing')


