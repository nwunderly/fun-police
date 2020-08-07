import aiohttp
import logging
import traceback
from bs4 import BeautifulSoup
from collections import defaultdict, namedtuple
from urllib.parse import urlparse, parse_qs

import discord
from discord.ext import commands

from utils.patterns import *
from utils.helpers import strip_url, get_domain
from utils.url import QuestionableURL
from confidential import authentication


logger = logging.getLogger('utils.detector')


RickRollData = namedtuple('RickRollData', ['check', 'extra'])
VIDEO_URL = "https://www.googleapis.com/youtube/v3/videos?key={key}&part=snippet&id={id}"
# check is name of check (redis, soup, comments, etc)
# extra is extra data (specific section for soup, percent of flagged comments, etc)


class YoutubeResolveError(Exception):
    pass


class YoutubeApiError(Exception):
    pass


class RickRollDetector:
    """
    Wraps up all methods used for checking a single message for rick rolls.
    """
    def __init__(self, bot, urls: list, session):
        self.bot = bot
        self.session = session
        self.redis = bot.redis
        self.base_url = "https://www.googleapis.com/youtube/v3/commentThreads?"

        # list of QuestionableURL objects
        self.urls = [QuestionableURL(url) for url in urls]

        # stripped final url: [stripped initial urls]
        self.redirects = defaultdict(set)

        # stripped final url: RickRollData
        self.rick_rolls = dict()

    async def find_rick_rolls(self):
        """
        Runs rickroll checks on any string, abstracted from process_rick_rolls for debugging.
        Returns breakdown of all detected rickroll links.
        """

        # remove duplicate URLs
        self.remove_dupes()

        # check redis cache
        # redis will have them cached without the http:// part
        await self.check_redis()

        # handle redirects
        # returns list of url strings and map of resolved url -> list of original urls
        await self.resolve()

        # check redis again, this time for any new URLs found after redirect
        await self.check_redis_again()

        # check for YouTube URLs
        # todo: non-youtube URLs should scrape and check for embedded YouTube video
        self.filter_youtube()

        # download YouTube pages and check with rick roll regex
        await self.check_youtube_video_data()

        # check comments for any YouTube URLs that haven't already been flagged
        await self.check_comments()

        return self.rick_rolls, self.redirects

    def remove_dupes(self):
        """
        Deletes duplicates from self.urls.
        """
        used = set()
        for url in list(self.urls):
            u = url.url()
            if u in used or not u:
                self.urls.remove(url)
            else:
                used.add(u)

    async def check_redis(self):
        """Checks redis cache for flagged URLs."""
        for url_obj in list(self.urls):
            url = url_obj.url()
            domain = url_obj.domain()

        # url
            logger.debug(f"CHECKING REDIS FOR URL {url}")
            redis = await self.redis.url_get(url)
            logger.debug(f"RESULT FROM REDIS: {redis}")
            if redis and isinstance(redis, dict):  # if not cached, will continue on to the next set of checks
                is_rick_roll = redis.get('is_rick_roll')
                logger.debug(f"is_rick_roll: {is_rick_roll}")

                if is_rick_roll is True:  # it's a cached rick roll

                    # this url is known to redirect to a rick roll
                    # slightly different procedure since output needs to include this information
                    if redis.get('detected_by') == 'redirect':
                        original_url = redis['extra']
                        self.redirects[original_url].add(url)
                        self.rick_rolls[original_url] = RickRollData('redis', 'redirect')

                    else:
                        detected_by = redis['detected_by']
                        self.rick_rolls[url] = RickRollData('redis', detected_by)

                    self.urls.remove(url_obj)

                elif is_rick_roll is False:  # it's a cached non-rick-roll
                    self.urls.remove(url_obj)  # it's been confirmed false, no longer needs to be checked

                else:  # weird error, invalid entry in redis, leaves this one in the list to be checked with other methods
                    logger.error(f"Database error, invalid result for URL: {url}")

                continue

        # domain
            redis = await self.redis.url_get(f"domain::{domain}")
            if redis and isinstance(redis, dict):  # if not cached, will continue on to the next set of checks
                is_rick_roll = redis.get('is_rick_roll')

                if is_rick_roll is True:  # it's a cached rick roll

                    # this domain is known to redirect all requests to a rick roll
                    # slightly different procedure since output needs to include this information
                    original_url = redis['extra']
                    self.redirects[original_url].add(url)
                    self.rick_rolls[original_url] = RickRollData('domain', original_url)
                    self.urls.remove(url_obj)  # no longer needs to be checked

                continue

    async def resolve(self):
        """
        Takes list of URL strings and returns list of resolved youtube urls.
        """

        async def get(_url, recursions=0):

            domain = get_domain(_url)
            logger.debug(f"DOMAIN: {domain}")
            if re.match(r'(?:.*\.)*(?:youtube\.com|youtu\.be)', domain):
                return _url

            async with self.session.get(_url, allow_redirects=False) as _response:
                if 300 <= _response.status <= 399:
                    location = _response.headers.get('Location')
                    logger.debug(f"URL {_url} redirects to {location}")
                    if location:
                        if recursions >= 3:
                            raise YoutubeResolveError("Too many redirects.")
                        return await get(location, recursions+1)

                raise YoutubeResolveError("URL does not redirect and is not a YouTube URL.")

        for url in list(self.urls):
            if not url:
                self.urls.remove(url)
                continue

            url_obj = url
            url = url.url()  # stripped=False?
            resolved = set()

            try:
                original_url = url
                if not url.startswith('http'):
                    url = 'http://' + url

                youtube_url = await get(url)
                url_obj.update(youtube_url)
                resolved_url = url_obj.url()

                if resolved_url in resolved:
                    # it resolves to a duplicate URL
                    url_obj.close()
                    self.urls.remove(url_obj)
                    if resolved_url != original_url:
                        self.redirects[resolved_url].add(original_url)
                else:
                    # same response is held open to be used again for downloading the page
                    if resolved_url != original_url:
                        self.redirects[resolved_url].add(original_url)
                    resolved.add(resolved_url)

            except (aiohttp.InvalidURL, aiohttp.ClientConnectorCertificateError, aiohttp.ClientConnectionError, YoutubeResolveError) as e:
                logger.debug(f"removing URL {url} ({e})")
                self.urls.remove(url_obj)


    async def check_redis_again(self):
        """Checks redis for any cached URLs after redirect."""
        for url_obj in list(self.urls):
            url = url_obj.url()

            logger.debug(f"CHECK_REDIS_AGAIN: CHECKING {url}")

            redis = await self.redis.url_get(url)
            if not redis or not isinstance(redis, dict):  # not cached, will continue on to the next set of checks
                continue
            is_rick_roll = redis.get('is_rick_roll')
            logger.debug(str(is_rick_roll))

            if is_rick_roll is True:  # it's a cached rick roll

                # this url is known to redirect to a rick roll
                # slightly different procedure since output needs to include this information
                if redis.get('detected_by') == 'redirect':
                    original_url = redis['extra']
                    self.redirects[original_url].add(url)
                    self.rick_rolls[original_url] = RickRollData('redis', 'redirect')

                # standard procedure, logs it and moves on.
                else:
                    # makes note that this is a rick roll along with the check that found it
                    self.rick_rolls[url] = RickRollData('redis', redis['detected_by'])

                self.urls.remove(url_obj)  # no longer needs to be checked

            elif is_rick_roll is False:  # it's a cached non-rick-roll
                self.urls.remove(url_obj)  # it's been confirmed false, no longer needs to be checked

            else:  # weird error, invalid entry in redis, leaves this one in the list to be checked with other methods
                logger.error(f"Database error, invalid result for URL: {url}")

    def filter_youtube(self):
        """
        Removes non-youtube URLs from list of Response objects
        """
        logger.debug("FILTER_YOUTUBE CALLED")
        for url_obj in list(self.urls):
            logger.debug(f"filter_youtube: url {url_obj.url()}, {url_obj.url(stripped=False)}")
            url = url_obj.url(stripped=False)
            match = yt_pattern.fullmatch(url)
            if not match:
                url_obj.close()
                self.urls.remove(url_obj)  # removes if not youtube, otherwise leaves it
                logger.debug(f"filter_youtube: removing URL {url}")
            else:
                logger.debug(f"filter_youtube: keeping URL {url}")

    async def check_youtube_video_data(self):
        """
        Uses web scraping to check YouTube page title, video title, and video description
        Returns updated rick roll data and URLs that tested negative (to be checked using YouTube API)
        """

        for url_obj in list(self.urls):
            url = url_obj.url()
            logger.debug(f"CHECK_YOUTUBE_VIDEO_DATA: {url}")

            parsed_url = urlparse(url)
            video_id = None

            # different methods for different urls.
            if get_domain(url).endswith("youtube.com"):
                v = parse_qs(parsed_url.query)
                if v:
                    # gets the video's id from the url's queries, specifically the `v` tag.
                    video_id = v.get('v')[0]

            elif parsed_url.netloc == "youtu.be":
                # returns the last characters of the shorter youtu.be url.
                video_id = parsed_url.path[1:]

            if video_id:

                # format the api url to request the video attached to this video_id.
                youtube_api_url = VIDEO_URL.format(key=authentication.YOUTUBE_API_KEY, id=video_id)

                response = await self.session.get(youtube_api_url)
                data = await response.json()

                try:
                    snippet = data['items'][0]["snippet"]  # if this line throws any errors I'm going to be angry

                    if len(list(rickroll_pattern.finditer(snippet["title"].lower()))) > 0:
                        self.rick_rolls[url] = RickRollData("youtube-api", "video-title")
                        url_obj.close()
                        self.urls.remove(url_obj)

                    elif len(list(rickroll_pattern.finditer(snippet["description"].lower()))) > 0:
                        self.rick_rolls[url] = RickRollData('youtube-api', 'video-description')
                        url_obj.close()
                        self.urls.remove(url_obj)

                    else:
                        # regex detected no rickrolls, don't remove from url list.
                        pass

                except KeyError:
                    logger.error(str(data))
                    if 'error' in data.keys():
                        raise YoutubeApiError(str(data['error']))
                    raise

    async def check_comments(self):
        """
        Uses YouTube API to pull up to 100 top comments and checks for clues using regex.
        """
        for url_obj in list(self.urls):
            url = url_obj.url(stripped=False)
            comments = await self.get_comments(url)
            is_rick_roll, percent, count = self.parse_comments(comments)
            if is_rick_roll:
                self.rick_rolls[strip_url(url_obj.url())] = RickRollData('comments', {'percent': percent, 'count': count})

    async def get_comments(self, url):
        """
        Pulls video comments using HTTP request to YouTube API.
        """
        url = url if isinstance(url, str) else url.human_repr()
        parsed_url = urlparse(url)
        video_id = None

        # different methods for different urls.
        if get_domain(url).endswith("youtube.com"):
            v = parse_qs(parsed_url.query)
            if v:
                # gets the video's id from the url's queries, specifically the `v` tag.
                video_id = v.get('v')[0]

        elif parsed_url.netloc == "youtu.be":
            # returns the last characters of the shorter youtu.be url.
            video_id = parsed_url.path[1:]

        if video_id:
            async with self.session.get(
                    f"{self.base_url}part=snippet&videoId={video_id}&textFormat=plainText&maxResults={self.bot.properties.comment_count}&key={authentication.YOUTUBE_API_KEY}") as response:
                json = await response.json()
                i = json.get('items')
                i = i if i else []
                return [str(item['snippet']) for item in i]

    @staticmethod
    def parse_comments(comments):
        """
        Runs regex search on list of comments and returns count/percent of matches.
        """
        count = 0
        if comments:
            for i in comments:
                m = len(list(comment_pattern.finditer(i.lower())))
                if m:
                    count += 1
            try:
                percent = (count / len(comments)) * 100
            except ZeroDivisionError:
                percent = 0
            if percent > 15 or count > 5:
                return True, percent, count
            else:
                return False, percent, count
        else:
            return False, 0, 0
