import aiohttp
import logging
import yaml
import traceback
from bs4 import BeautifulSoup
from collections import defaultdict, namedtuple

import discord
from discord.ext import commands

# custom imports
from bot.astley import Astley
from utils.patterns import *
from utils.helpers import strip_url
from confidential import authentication


logger = logging.getLogger("bot.rick")

RickRollData = namedtuple('RickRollData', ['check', 'extra'])
# check is name of check (redis, soup, comments, etc)
# extra is extra data (specific section for soup, percent of flagged comments, etc)


class Rick(Astley):
    """
    A bot that detects and warns you about possible Rick rolls.
    """
    def __init__(self):
        super().__init__()
        self.url_pattern = url_pattern
        self.yt_pattern = yt_pattern
        self.rickroll_pattern = rickroll_pattern
        self.comment_pattern = comment_pattern
        self.base_url = "https://www.googleapis.com/youtube/v3/commentThreads?"

    async def on_message(self, message):
        if message.author == self.user or message.author.id in [687454860907511881, 715258929155932273]:
            return
        await self.process_commands(message)
        if not message.content.lower().startswith(f'{self.command_prefix}check') \
                and not message.content.lower().startswith(f'{self.command_prefix}report') \
                and not message.content.lower().startswith(f'{self.command_prefix}remove'):
            try:
                await self.process_rick_rolls(message)
            except Exception as e:
                exc = traceback.format_exception(e.__class__, e, e.__traceback__)
                exc = '\n'.join(exc)
                logger.error(f"Exception occurred in on_message {message.jump_url}>\n{exc}")
                hook = discord.Webhook.from_url(authentication.WEBHOOKS['errors'], adapter=discord.AsyncWebhookAdapter(self.session))
                try:
                    await hook.send(f"Exception occurred in [on_message](<{message.jump_url}>):```py\n{exc[:1850]}\n```")
                except discord.DiscordException:
                    logger.error("Failed to log error to logging channel.")

    async def on_message_edit(self, before, after):
        if before.content == after.content:
            return
        message = after
        try:
            await self.process_rick_rolls(message)
        except Exception as e:
            exc = traceback.format_exception(e.__class__, e, e.__traceback__)
            exc = '\n'.join(exc)
            logger.error(f"Exception occurred in on_message_edit {message.jump_url}>\n{exc}")
            hook = discord.Webhook.from_url(authentication.WEBHOOKS['errors'], adapter=discord.AsyncWebhookAdapter(self.session))
            try:
                await hook.send(f"Exception occurred in [on_message_edit](<{message.jump_url}>):```py\n{exc[:1850]}\n```")
            except discord.DiscordException:
                logger.error("Failed to log error to logging channel.")

    def get_urls(self, s):
        return [match.group(0) for match in self.url_pattern.finditer(s)]

    def is_youtube(self, url):
        return self.yt_pattern.fullmatch(url)

    async def process_results(self, message, rick_rolls: dict, redirects: dict):
        print("RICK_ROLLS")
        print(rick_rolls)
        print("REDIRECTS")
        print(redirects)
        if len(rick_rolls) > 1:
            urls = ""
            for url, info in rick_rolls.items():
                original = redirects[url]
                check = rick_rolls[url].check
                extra = rick_rolls[url].extra
                if original:
                    for og in original:
                        urls += f"\n{og} -> {url}"
                elif check == 'redirect':
                    urls += f"\n{original} -> {extra}"
                else:
                    urls += f"\n{url}"
            await message.channel.send(f"**⚠ Detected Rickroll at {len(rick_rolls)} URLs:\n**{urls}")
        else:
            url = list(rick_rolls.keys())[0]
            original = redirects[url]
            if original:
                url = f"\n{', '.join(original)} -> {url}"
            elif rick_rolls[url].check == 'redirect':
                url = f"\n{original} -> {rick_rolls[url].extra}"
            await message.channel.send(f"**⚠ Detected Rickroll at URL:\n**```{url}```")

    async def process_rick_rolls(self, message):
        """
        Calls find_rick_rolls, then processes results, sends a message if necessary and adds any rick rolls found to redis cache.
        Returns True or False depending on whether any rick rolls were found.
        :param message: discord Message object to be checked.
        :return: list of dicts, each with "is_rick_roll" and "extra" fields.
        """
        logger.debug(f"Checking message {message.id}.")
        urls = self.get_urls(message.content)
        
        if not urls:
            return

        rick_rolls, redirects = await self.find_rick_rolls(urls)

        if not rick_rolls:
            return

        await self.process_results(message, rick_rolls, redirects)

        # write new rick rolls to Redis
        # todo: cache non-rick-rolls too
        for url, data in rick_rolls.items():
            if data.check != 'redis':
                await self.redis.url_set(url, True, data.check, data.extra)
            for original_url in redirects[url]:  # defaultdict so returns empty list if no associated redirects
                await self.redis.url_set(original_url, True, 'redirect', url)

        return bool(rick_rolls)

    async def find_rick_rolls(self, urls):
        """
        Runs rickroll checks on any string, abstracted from process_rick_rolls for debugging.
        Returns breakdown of all detected rickroll links.
        """
        rick_rolls = dict()  # key: url, value: name of first check that caught this url
        redirects = defaultdict(list)  # key: original url, value: resolved url

        # URLs in message
        original_urls = [url for url in urls]

        # remove duplicate URLs by stripping "http://www." and passing through set()
        urls = set([strip_url(url) for url in urls if url])

        # check redis cache
        # redis will have them cached without the http:// part
        rick_rolls, urls, redirects = await self.check_redis(rick_rolls, urls, redirects)

        # handle redirects
        # returns list of Response objects and map of resolved url -> list of original urls
        responses, redirects = await self.resolve(urls, redirects)

        # check redis again, this time for any new URLs found after redirect
        redirect_urls = [strip_url(response.url.human_repr()) for response in responses if response.url.human_repr() not in original_urls]
        rick_rolls, urls, _ = await self.check_redis(rick_rolls, redirect_urls, {})

        # check for YouTube URLs
        # todo: non-youtube URLs should scrape and check for embedded YouTube video
        responses = self.filter_youtube(responses)

        # download YouTube pages and check with rick roll regex
        rick_rolls, urls = await self.check_youtube_html(rick_rolls, responses)

        # check comments for any YouTube URLs that haven't already been flagged
        rick_rolls = await self.check_comments(rick_rolls, urls)

        return rick_rolls, redirects

    async def check_redis(self, rick_rolls, urls, redirects):
        urls = [strip_url(url) for url in urls]
        for url in list(urls):
            if not url:
                urls.remove(url)
                continue
            redis = await self.redis.url_get(url)
            if not redis or not isinstance(redis, dict):  # not cached, will continue on to the next set of checks
                continue
            is_rick_roll = redis.get('is_rick_roll')
            if is_rick_roll is True:  # it's a cached rick roll
                if redis.get('detected_by') == 'redirect':
                    redirects[redis['extra']].append(url)
                    rick_rolls[redis['extra']] = RickRollData('redis', redis['detected_by'])
                else:
                    rick_rolls[url] = RickRollData('redis', redis['detected_by'])  # makes note that this is a rick roll along with the check that found it
                urls.remove(url)  # no longer needs to be checked
            elif is_rick_roll is False:  # it's a cached non-rick-roll
                urls.remove(url)  # it's been confirmed false, no longer needs to be checked
            else:
                logger.error(f"Database error, invalid result for URL: {url}")
        return rick_rolls, urls, redirects

    async def resolve(self, urls, redirects):
        """
        Takes list of URL strings and returns list of Response objects with resolved URLs.
        """
        responses = list()  # list of response objects to be passed on to next part
        resolved = set()

        for url in list(urls):
            if not url:
                urls.remove(url)
                continue
            try:
                if not url.startswith('http'):
                    url = 'http://' + url
                response = await self.session.get(url)
                resolved_url = response.url.human_repr()
                if resolved_url not in resolved:
                    responses.append(response)  # same response is held open to be used again for downloading the page
                    if resolved_url != url:
                        redirects[strip_url(response.url.human_repr())].append(strip_url(url))
                    resolved.add(resolved_url)
                else:  # it resolves to a duplicate URL
                    # await response.release()
                    response.close()
                    if resolved_url != url:
                        redirects[strip_url(response.url.human_repr())].append(strip_url(url))
            except (aiohttp.InvalidURL, aiohttp.ClientConnectorCertificateError):
                pass
        return responses, redirects

    def filter_youtube(self, responses):
        """
        Removes non-youtube URLs from list of Response objects
        """
        for response in (list(responses) if responses else []):
            match = self.yt_pattern.fullmatch(response.url.human_repr())
            if not match:
                # await response.release()
                response.close()
                responses.remove(response)  # removes if not youtube, otherwise leaves it
        return responses

    async def check_youtube_html(self, rick_rolls, responses):
        """
        Uses web scraping to check YouTube page title, video title, and video description
        Returns updated rick roll data and URLs that tested negative (to be checked using YouTube API)
        """
        urls = list()

        for response in (list(responses) if responses else []):

            # PARTIAL READ IS CURRENTLY BROKEN - DO NOT USE
            # data = await response.content.read(10**6)  # reads up to 1 megabyte
            # html = data.decode()

            html = await response.read()

            soup = BeautifulSoup(html, features="html.parser")

            try:
                # check page title
                if len(list(rickroll_pattern.finditer(soup.head.title.text.lower()))) > 0:
                    url = strip_url(response.url)
                    rick_rolls[url] = RickRollData('soup', 'page-title')

                # check video title
                elif len(list(rickroll_pattern.finditer(soup.find(id='eow-title').text.lower()))) > 0:
                    url = strip_url(response.url)
                    rick_rolls[url] = RickRollData('soup', 'video-title')

                # check video description
                elif len(list(rickroll_pattern.finditer(soup.find(id='eow-description').text.lower()))) > 0:
                    url = strip_url(response.url)
                    rick_rolls[url] = RickRollData('soup', 'video-description')

                # check SME recommended video (youtube automatically adds this when it detects a song)
                elif len(list(rickroll_pattern.finditer(soup.find('ul', {'class': 'watch-extras-section'}).text.lower()))) > 0:
                    url = strip_url(response.url.human_repr())
                    rick_rolls[url] = RickRollData('soup', 'recommended')

                else:
                    urls.append(response.url.human_repr())

            except AttributeError as e:
                exc = traceback.format_exception(e.__class__, e, e.__traceback__)
                exc = '\n'.join(exc)
                logger.error(f"SOUP ERROR DETECTED\nWITH URL {response.url}\nHTTP CODE {response.status}\nHTML\n{html}\nTRACEBACK\n{exc}")
                hook = discord.Webhook.from_url(authentication.WEBHOOKS['errors'], adapter=discord.AsyncWebhookAdapter(self.session))
                try:
                    await hook.send(f"SOUP ERROR DETECTED\nWITH URL <{response.url}>\nHTTP CODE {response.status}")
                except discord.DiscordException:
                    logger.error("Failed to log error to logging channel.")

        return rick_rolls, urls
                
    async def check_comments(self, rick_rolls, urls):
        """
        Uses YouTube API to pull up to 100 top comments and checks for clues using regex.
        """
        urls = [url if isinstance(url, str) else url.human_repr() for url in urls]
        for url in urls:
            comments = await self.get_comments(url)
            is_rick_roll, percent, count = self.parse_comments(comments)
            if is_rick_roll:
                rick_rolls[strip_url(url)] = RickRollData('comments', {'percent': percent, 'count': count})
        return rick_rolls
    
    async def get_comments(self, url):
        """
        Pulls video comments using HTTP request to YouTube API.
        """
        url = url if isinstance(url, str) else url.human_repr()
        url_id = re.sub('youtube.com/watch?v=', '', url)
        async with self.session.get(f"{self.base_url}part=snippet&videoId={url_id}&textFormat=plainText&maxResults={self.properties.comment_count}&key={authentication.YOUTUBE_API_KEY}") as response:
            json = await response.json()
            i = json.get('items')
            i = i if i else []
            return [str(item['snippet']) for item in i]

    def parse_comments(self, comments):
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

    async def setup(self):
        for cog in self.properties.cogs:
            try:
                self.load_extension(cog)
            except commands.ExtensionFailed as exception:
                traceback.print_exception(type(exception), exception, exception.__traceback__)

    async def cleanup(self):
        await self.session.close()



