
import aiohttp
import logging
import traceback
from bs4 import BeautifulSoup
from collections import defaultdict, namedtuple

import discord
from discord.ext import commands

from utils.patterns import *
from utils.helpers import strip_url
from utils.url import QuestionableURL
from confidential import authentication


logger = logging.getLogger('utils.detector')


RickRollData = namedtuple('RickRollData', ['check', 'extra'])
# check is name of check (redis, soup, comments, etc)
# extra is extra data (specific section for soup, percent of flagged comments, etc)


class RickRollDetector:
    """
    Wraps up all methods used for checking a single message for rick rolls.
    """
    def __init__(self, bot, urls: list):
        self.bot = bot
        self.session = bot.session
        self.redis = bot.redis
        self.base_url = "https://www.googleapis.com/youtube/v3/commentThreads?"

        # list of QuestionableURL objects
        self.urls = [QuestionableURL(url) for url in urls]

        # stripped final url: [stripped initial urls]
        self.redirects = defaultdict(list)

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
        # returns list of Response objects and map of resolved url -> list of original urls
        await self.resolve()

        # check redis again, this time for any new URLs found after redirect
        await self.check_redis_again()

        # check for YouTube URLs
        # todo: non-youtube URLs should scrape and check for embedded YouTube video
        self.filter_youtube()

        # download YouTube pages and check with rick roll regex
        await self.check_youtube_html()

        # check comments for any YouTube URLs that haven't already been flagged
        await self.check_comments()

        return self.rick_rolls, self.redirects

    def remove_dupes(self):
        """
        Deletes duplicates from self.urls.
        """
        used = set()
        for url in self.urls:
            u = url.url()
            if u in used or not u:
                self.urls.remove(url)
            else:
                used.add(u)

    async def check_redis(self):
        """Checks redis cache for flagged URLs."""
        for url_obj in self.urls:
            url = url_obj.url()
            domain = url_obj.domain()

        # domain
            print(f"DOMAIN: {domain}")
            redis = await self.redis.url_get(f"domain::{domain}")
            if redis and isinstance(redis, dict):  # if not cached, will continue on to the next set of checks
                is_rick_roll = redis.get('is_rick_roll')

                if is_rick_roll is True:  # it's a cached rick roll

                    # this domain is known to redirect all requests to a rick roll
                    # slightly different procedure since output needs to include this information
                    original_url = redis['extra']
                    self.redirects[original_url].append(url)
                    self.rick_rolls[original_url] = RickRollData('domain', original_url)
                    self.urls.remove(url_obj)  # no longer needs to be checked

                continue

        # url
            redis = await self.redis.url_get(url)
            if redis and isinstance(redis, dict):  # if not cached, will continue on to the next set of checks
                is_rick_roll = redis.get('is_rick_roll')

                if is_rick_roll is True:  # it's a cached rick roll

                    # this url is known to redirect to a rick roll
                    # slightly different procedure since output needs to include this information
                    if redis.get('detected_by') == 'redirect':
                        original_url = redis['extra']
                        self.redirects[original_url].append(url)
                        self.rick_rolls[original_url] = RickRollData('redis', 'redirect')

                elif is_rick_roll is False:  # it's a cached non-rick-roll
                    self.urls.remove(url_obj)  # it's been confirmed false, no longer needs to be checked

                else:  # weird error, invalid entry in redis, leaves this one in the list to be checked with other methods
                    logger.error(f"Database error, invalid result for URL: {url}")

                continue

        # # domain
        #     redis = await self.redis.url_get(f"domain::{domain}")
        #     if redis and isinstance(redis, dict):  # if not cached, will continue on to the next set of checks
        #         is_rick_roll = redis.get('is_rick_roll')
        #
        #         if is_rick_roll is True:  # it's a cached rick roll
        #
        #             # this domain is known to redirect all requests to a rick roll
        #             # slightly different procedure since output needs to include this information
        #             original_url = redis['extra']
        #             self.redirects[original_url].append(url)
        #             self.rick_rolls[original_url] = RickRollData('domain', original_url)
        #             self.urls.remove(url_obj)  # no longer needs to be checked
        #
        #         return

    async def resolve(self):
        """
        Takes list of URL strings and returns list of Response objects with resolved URLs.
        """

        for url in self.urls:
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

                response = await self.session.get(url)
                url_obj.update(response)
                resolved_url = url_obj.url()

                if resolved_url in resolved:
                    # it resolves to a duplicate URL
                    url_obj.close()
                    self.urls.remove(url_obj)
                    if resolved_url != url:
                        self.redirects[resolved_url].append(original_url)
                else:
                    # same response is held open to be used again for downloading the page
                    if resolved_url != url:
                        self.redirects[resolved_url].append(original_url)
                    resolved.add(resolved_url)

            except (aiohttp.InvalidURL, aiohttp.ClientConnectorCertificateError):
                self.urls.remove(url_obj)

    async def check_redis_again(self):
        """Checks redis for any cached URLs after redirect."""
        for url_obj in self.urls:
            url = url_obj.url()

            redis = await self.redis.url_get(url)
            if not redis or not isinstance(redis, dict):  # not cached, will continue on to the next set of checks
                continue
            is_rick_roll = redis.get('is_rick_roll')

            if is_rick_roll is True:  # it's a cached rick roll

                # this url is known to redirect to a rick roll
                # slightly different procedure since output needs to include this information
                if redis.get('detected_by') == 'redirect':
                    original_url = redis['extra']
                    print(f"105: adding {url} to redirect list")
                    self.redirects[original_url].append(url)
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
        for url_obj in self.urls:
            url = url_obj.url()
            match = yt_pattern.fullmatch(url)
            if not match:
                url_obj.close()
                self.urls.remove(url_obj)  # removes if not youtube, otherwise leaves it
                logger.debug(f"filter_youtube: removing URL {url}")
            else:
                logger.debug(f"filter_youtube: keeping URL {url}")

    async def check_youtube_html(self):
        """
        Uses web scraping to check YouTube page title, video title, and video description
        Returns updated rick roll data and URLs that tested negative (to be checked using YouTube API)
        """

        for url_obj in self.urls:
            url = url_obj.url()

            # PARTIAL READ IS CURRENTLY BROKEN - DO NOT USE
            # data = await response.content.read(10**6)  # reads up to 1 megabyte
            # html = data.decode()

            html = await url_obj.read()

            soup = BeautifulSoup(html, features="html.parser")

            try:
                # check page title
                if len(list(rickroll_pattern.finditer(soup.head.title.text.lower()))) > 0:
                    self.rick_rolls[url] = RickRollData('soup', 'page-title')
                    url_obj.close()
                    self.urls.remove(url_obj)

                # check video title
                elif len(list(rickroll_pattern.finditer(soup.find(id='eow-title').text.lower()))) > 0:
                    self.rick_rolls[url] = RickRollData('soup', 'video-title')
                    url_obj.close()
                    self.urls.remove(url_obj)

                # check video description
                elif len(list(rickroll_pattern.finditer(soup.find(id='eow-description').text.lower()))) > 0:
                    self.rick_rolls[url] = RickRollData('soup', 'video-description')
                    url_obj.close()
                    self.urls.remove(url_obj)

                # check SME recommended video (youtube automatically adds this when it detects a song)
                elif len(list(rickroll_pattern.finditer(soup.find('ul', {'class': 'watch-extras-section'}).text.lower()))) > 0:
                    self.rick_rolls[url] = RickRollData('soup', 'recommended')
                    url_obj.close()
                    self.urls.remove(url_obj)

                else:
                    # regex did not return positive, do not remove url from list
                    # self.urls will be all URLs that haven't been checked yet.
                    pass

            except AttributeError as e:
                exc = traceback.format_exception(e.__class__, e, e.__traceback__)
                exc = '\n'.join(exc)
                logger.error(f"SOUP ERROR DETECTED\nWITH URL {url_obj.url(stripped=False)}\nHTTP CODE {url_obj.response.status}\nHTML\n{html}\nTRACEBACK\n{exc}")
                hook = discord.Webhook.from_url(authentication.WEBHOOKS['errors'], adapter=discord.AsyncWebhookAdapter(self.session))
                try:
                    await hook.send(f"SOUP ERROR DETECTED\nWITH URL <{url_obj.url(stripped=False)}>\nHTTP CODE {url_obj.response.status}")
                except discord.DiscordException:
                    logger.error("Failed to log error to logging channel.")

    async def check_comments(self):
        """
        Uses YouTube API to pull up to 100 top comments and checks for clues using regex.
        """
        for url_obj in self.urls:
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
        url_id = re.sub('youtube.com/watch?v=', '', url)
        async with self.session.get(
                f"{self.base_url}part=snippet&videoId={url_id}&textFormat=plainText&maxResults={self.bot.properties.comment_count}&key={authentication.YOUTUBE_API_KEY}") as response:
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


