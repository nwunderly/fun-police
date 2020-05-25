import aiohttp
import logging


logger = logging.getLogger('utils.http')


class HTTP(aiohttp.ClientSession):
    """
    Custom async HTTP client.
    """

    async def resolve(self, *urls):
        pass




