
import aiohttp
import asyncio


async def get(url):
    async with aiohttp.ClientSession() as session:
        async with session.get(url, allow_redirects=False) as response:
            print(response.status)
            print(response.headers)


asyncio.run(get('http://ter.ps/bikinibottom'))
