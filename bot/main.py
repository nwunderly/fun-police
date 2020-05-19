
import aiohttp
import yaml
from collections import defaultdict

# custom imports
from utils.helpers import setup_logger
from bot.backend import Astley
from utils import patterns


logger = setup_logger("Rick")


class Rick(Astley):
    """
    A bot that detects and warns you about possible Rick rolls.
    """
    def __init__(self):
        super().__init__(command_prefix="!!")
        self.url_pattern = patterns.url_pattern
        self.yt_pattern = patterns.yt_pattern

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
        return self.url_pattern.finditer(s)

    def is_youtube(self, url):
        return self.yt_pattern.fullmatch(url)

    async def resolve(self, *urls):
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
        pass

    async def process_results(self, results):
        """
        Results will be a dict of scanner names mapped to floats.
        This function will process overall results and make the final judgement.
        """
        for key, value in results.items():
            if value > 0:
                return True
        return False

    async def setup(self):
        self.load_extension('utils.testing')
        # self.scanners.append(urlchecker.URLChecker())



