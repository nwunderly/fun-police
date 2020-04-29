
import asyncio
import aiohttp
from bs4 import BeautifulSoup


class YouTubeClient:
    def __init__(self, session):
        self.session = session

    async def get_page(self, url):
        async with self.session.get(url) as response:
            return await response.text()

    def process_page(self, html):
        data = dict()
        soup = BeautifulSoup(html, features="html.parser")
        data['page_title'] = soup.head.title.text
        result = soup.find(id='eow-title')
        data['vid_title'] = result.text if result else ''
        result = soup.find(id='eow-description')
        data['vid_description'] = result.text if result else ''
        return data

    async def get_data(self, url):
        html = await self.get_page(url)
        data = self.process_page(html)
        return data
