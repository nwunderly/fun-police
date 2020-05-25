import asyncio
import aiohttp
import logging
from bs4 import BeautifulSoup

from utils import http

logger = logging.getLogger('utils.soup')


"""
Utility file to aid with BeautifulSoup web scraping.
"""


class Soup(http.HTTP):
    """
    Specialized HTTP client for web scraping.
    """


