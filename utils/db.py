
import boto3
import aioboto3
import redis
import aredis

import datetime
import logging

logger = logging.getLogger('utils.db')


"""
Intended support for both synchronous and async versions of DynamoDB as well as Redis.
Honestly only making them all because the standard, synchronous ones are definitely more stable.
"""


class DynamoTable:
    """
    Not implemented yet.
    Currently not necessary but could be useful in the future.
    """


class AsyncDynamoTable:  # maybe make awaitable later
    """
    Async DynamoDB Table class.
    Use with "async with" context.

    I have no idea if this fucking works, good thing we probably won't need it
    """
    def __init__(self, name):
        self._resource = None
        self._table = None
        self.name = name

    # I have no idea if this is how you do it
    # def __await__(self):
    #     return self

    async def __aenter__(self):
        self._resource = await aioboto3.resource('dynamodb').__aenter__()
        self._table = await self._resource.Table(self.name)

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self._resource.__aexit__(exc_type, exc_val, exc_tb)


class RedisCache(redis.Redis):
    """
    Synchronous Redis wrapper, made this because it should be a more stable alternative if needed.
    Currently doesn't do anything but will allow for addition of custom methods as needed.
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
        super().__init__(host='localhost', port=6379, db=0)

    async def url_set(self, url, is_rick_roll, detected_by, extra, *args, **kwargs):
        """
        Modified implementation of set() that handles metadata for items.
        """
        if url.startswith('http://'):
            url = url[7:]
        elif url.startswith('https://'):
            url = url[8:]
        data = {
            'is_rick_roll': is_rick_roll,
            'timestamp': str(datetime.datetime.now()),
            'detected_by': detected_by,
            'extra': extra,
            'verified': False}
        await self.set(url, data, *args, **kwargs)

    async def url_get(self, url):
        url = url.replace('http://', '').replace('https://', '')
        response = await self.get(url)
        if response:
            data = eval(response.decode())
            return data
        else:
            return None


