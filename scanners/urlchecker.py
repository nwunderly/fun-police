
import re
import aiohttp

from utils.helpers import setup_logger
from scanners.scanner import Scanner


logger = setup_logger('url-checker')


class URLChecker(Scanner):
    """
    Regexes a message to search for YouTube URLs.
    Intended to be reworked and implemented in a pre-scan check for real release.
    """
    def __init__(self):
        self.name = "URL Checker"
        self.url = re.compile(r"""(?:(?:https?|ftp)://|\b(?:[a-z\d]+\.))(?:(?:[^\s()<>]+|\((?:[^\s()<>]+|(?:\([^\s()<>]+\)))?\))+(?:\((?:[^\s()<>]+|(?:\(?:[^\s()<>]+\)))?\)|[^\s`!()\[\]{};:'".,<>?«»“”‘’]))?""")
        self.youtube = re.compile(r"""^((?:https?:)?//)?((?:www|m)\.)?((?:youtube\.com|youtu.be))(/(?:[\w\-]+\?v=|embed/|v/)?)([\w\-]+)(\S+)?$""")

    def reformat(self, message):
        return (message.content,), {}

    async def scanner(self, message_content):
        matches = self.url.finditer(message_content)
        for match in matches:
            logger.debug(f"Matched URL: {match.group(0)}")
            result = await self.check_for_youtube(match.group(0))
            if result:
                return 1
        return 0

    async def check_for_youtube(self, url):
        match = self.youtube.fullmatch(url)
        if match:
            logger.debug(f"Matched YouTube URL: {match.group(0)}")
            return True
        async with aiohttp.ClientSession() as session:
            async with session.head(url, allow_redirects=True) as response:
                match = self.youtube.fullmatch(response.url.human_repr())
                if match:
                    logger.debug(f"Matched YouTube URL: {match.group(0)}")
                    return True
        return False





