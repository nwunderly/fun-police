
import aiohttp

# custom imports
from utils.helpers import setup_logger
from bot.backend import Astley
from scanners.scanner import ScanResults
from scanners import urlchecker


logger = setup_logger("Rick")


class Rick(Astley):
    """
    A bot that detects and warns you about possible Rick rolls.
    """
    def __init__(self):
        super().__init__(command_prefix="rr!")
        self.scanners = list()
        self.url_patterns = dict()
        self.youtube_url_patterns = dict()

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
        status = ""
        identified_urls = await self.process_urls(message.content)
        status += f"RESULTS FROM URL REGEX\n"
        resolved_urls = await self.process_redirects(identified_urls)
        status += f"RESULTS FROM REDIRECT CHASING\n"
        identified_youtube = await self.process_youtube_urls(resolved_urls)
        status += f"RESULTS FROM YOUTUBE REDIRECTS\n"

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
            matches[name] = [match.group(0) for match in match_list]
        return matches

    async def process_redirects(self, urls):
        resolved = list()
        async with aiohttp.ClientSession() as session:
            for url in urls:
                async with session.head(url, allow_redirects=True) as response:
                    resolved.append(response.url.human_repr())
        return resolved

    async def process_youtube_urls(self, urls):
        matches = dict()
        for name, pattern in self.youtube_url_patterns.items():
            match = pattern.fullmatch(urls)
            if match:
                logger.debug(f"Matched YouTube URL: {match.group(0)}")
                matches[name] = match.group(0)

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
        self.scanners.append(urlchecker.URLChecker())



