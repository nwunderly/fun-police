import datetime
import logging

import aredis

from utils.helpers import strip_url

logger = logging.getLogger("utils.db")


"""
Intended support for both synchronous and async versions of Redis.
"""


class AsyncRedis(aredis.StrictRedis):
    """
    Async Redis wrapper. Allows for addition of custom methods.

    useful methods:
     - get(name)
     - set(name, value)
     - save()
     - lastsave()
     - flushdb()   ===DO NOT USE THIS===
    """

    def __init__(self):
        super().__init__(host="redis", port=6379, db=0)

    async def url_set(self, url, is_rick_roll, detected_by, extra, *args, **kwargs):
        """
        Modified implementation of set() that handles metadata for items.
        """
        url = strip_url(url)
        data = {
            "is_rick_roll": is_rick_roll,
            "timestamp": str(datetime.datetime.now()),
            "detected_by": detected_by,
            "extra": extra,
        }
        await self.set(url, data, *args, **kwargs)

    async def url_get(self, url):
        url = strip_url(url)
        response = await self.get(url)
        if response:
            data = eval(response.decode())
            return data
        else:
            return None
