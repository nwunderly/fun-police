
import asyncio
import aiohttp
from bs4 import BeautifulSoup


class YouTubeClient:
    def __init__(self, session):
        self.session = session

    async def get_page(self, url):
        async with self.session.get(url) as response:
            return await response.text()

    def get_page_info(self, html):
        soup = BeautifulSoup(html, features="html.parser")
        print(soup.head.title.text)
        result = soup.find(id='eow-description')
        print(result.text)
        result = soup.find(id='eow-title')
        print(result.text)


async def main():
    async with aiohttp.ClientSession() as session:
        client = YouTubeClient(session)
        html = await client.get_page('https://www.youtube.com/watch?v=kR0gOEyK6Tg')
        client.get_page_info(html)


if __name__ == "__main__":
    asyncio.run(main())

