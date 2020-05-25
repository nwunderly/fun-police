
import asyncio
import aiohttp
import logging
from bs4 import BeautifulSoup

logger = logging.getLogger('utils.soup')


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
        ul = soup.find('ul', {'class': 'watch-extras-section'})
        data['recommended'] = ul.find_all('li')[3].text if ul else ''
        print(data)
        return data

    async def get_data(self, url):
        html = await self.get_page(url)
        data = self.process_page(html)
        return data
