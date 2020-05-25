import aiohttp
import logging

from utils import http

logger = logging.getLogger('utils.api')


"""
Utility file to assist with YouTube API calls.
"""


class YoutubeAPIClient(http.HTTP):
    """
    Specialized HTTP client for YouTube API calls.
    """


