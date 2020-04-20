
import aiohttp
import yaml
from collections import defaultdict

# custom imports
from utils.helpers import setup_logger
from bot.backend import Astley
from scanners.scanner import ScanResults
from scanners import urlchecker

from utils.patterns import url, youtube


logger = setup_logger("Rick")


class Rick(Astley):
    """
    A bot that detects and warns you about possible Rick rolls.
    """
    def __init__(self):
        super().__init__(command_prefix="!!")
        self.scanners = list()
        self.url_patterns = url
        self.youtube_url_patterns = youtube

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

    async def process_rick_rolls(self, message):
        logger.debug(f"Checking message {message.id}.")
        status = f"Results from message `{message.id}`\n"
        identified_urls = await self.process_urls(message.content)
        status += f"\nIdentified URLs:\n{yaml.dump(identified_urls)}"
        resolved_urls = await self.process_redirects(identified_urls.values())
        status += f"\nURLs after redirect processing:\n{yaml.dump(resolved_urls)}"
        identified_youtube = await self.process_youtube_urls(resolved_urls)
        status += f"\nIdentified YouTube URLs:\n{yaml.dump(identified_youtube)}"

        await message.channel.send(status)

        # results = dict()
        # for scanner in self.scanners:
        #     result = await scanner.scan(message)
        #     results[scanner.name] = result
        # if await self.process_results(results):
        #     s = f"Url in the previous message triggered the following scanners:"
        #     for key, value in results.items():
        #         if isinstance(value, ScanResults) or value > 0:
        #             s += f"\n{key}: {value}"
        #     await message.channel.send(s)
        # else:
        #     logger.debug(f"Nothing of note found in message {message.id}.")

    async def process_urls(self, content):
        matches = dict()
        for name, pattern in self.url_patterns.items():
            match_list = pattern.finditer(content)
            matches[name] = [str(match.group(0)) for match in match_list]
        return matches

    async def process_redirects(self, urls):
        resolved = list()
        checked_urls = list()
        async with aiohttp.ClientSession() as session:
            for _url_list in urls:
                for _url in _url_list:
                    if _url not in checked_urls:
                        try:
                            if not _url.startswith('http'):
                                _url = 'http://' + _url
                            async with session.head(_url, allow_redirects=True) as response:
                                resolved_url = response.url.human_repr()
                                if resolved_url not in checked_urls:
                                    resolved.append(resolved_url)
                                    checked_urls.append(resolved_url)
                        except aiohttp.InvalidURL:
                            pass
                        checked_urls.append(_url)
        return resolved

    async def process_youtube_urls(self, urls):
        matches = defaultdict(list)
        for name, pattern in self.youtube_url_patterns.items():
            for url in urls:
                match = pattern.fullmatch(url)
                if match:
                    logger.debug(f"Matched YouTube URL: {match.group(0)}")
                    matches[name].append(match.group(0))
        return matches

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
        pass
        # self.scanners.append(urlchecker.URLChecker())



