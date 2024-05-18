import logging
import traceback

import aiohttp
import discord
from discord.ext import commands

import auth

# custom imports
from bot.astley import Astley
from utils.detector import RickRollDetector
from utils.patterns import *

logger = logging.getLogger("bot.rick")


class Rick(Astley):
    """
    A bot that detects and warns you about possible Rickrolls.
    """

    def __init__(self):
        super().__init__()
        self.description = "The best Discord bot for detecting Rickrolls."
        self.url_pattern = url_pattern
        self.yt_pattern = yt_pattern
        self.rickroll_pattern = rickroll_pattern
        self.comment_pattern = comment_pattern
        self.stats = None
        self.ignored_guilds = [264445053596991498, 110373943822540800]

    async def on_message(self, message):
        if not message.guild:
            return
        if message.author == self.user or message.author.id in [
            687454860907511881,
            715258929155932273,
        ]:
            return
        await self.process_commands(message)
        if message.guild.id in self.ignored_guilds:
            return
        if (
            not message.content.lower().startswith(f"{self.command_prefix}check")
            and not message.content.lower().startswith(f"{self.command_prefix}report")
            and not message.content.lower().startswith(f"{self.command_prefix}remove")
        ):
            try:
                await self.process_rick_rolls(message)
            except Exception as e:
                exc = traceback.format_exception(e.__class__, e, e.__traceback__)
                exc = "\n".join(exc)
                logger.error(
                    f"Exception occurred in on_message {message.jump_url}\n{exc}"
                )
                hook = discord.Webhook.from_url(
                    auth.WEBHOOKS["errors"],
                    session=self.session,
                )
                try:
                    await hook.send(
                        f"Exception occurred in [on_message](<{message.jump_url}>):```py\n{exc[:1850]}\n```"
                    )
                except discord.DiscordException:
                    logger.error("Failed to log error to logging channel.")

    async def on_message_edit(self, before, after):
        if before.content == after.content:
            return
        message = after
        if message.guild.id in self.ignored_guilds:
            return
        try:
            await self.process_rick_rolls(after)
        except Exception as e:
            exc = traceback.format_exception(e.__class__, e, e.__traceback__)
            exc = "\n".join(exc)
            logger.error(
                f"Exception occurred in on_message_edit {message.jump_url}\n{exc}"
            )
            hook = discord.Webhook.from_url(
                auth.WEBHOOKS["errors"],
                session=self.session,
            )
            try:
                await hook.send(
                    f"Exception occurred in [on_message_edit](<{message.jump_url}>):```py\n{exc[:1850]}\n```"
                )
            except discord.DiscordException:
                logger.error("Failed to log error to logging channel.")

    def get_urls(self, s):
        return [match.group(0) for match in self.url_pattern.finditer(s)]

    def is_youtube(self, url):
        return self.yt_pattern.fullmatch(url)

    async def process_results(self, message, rick_rolls: dict, redirects: dict):
        logger.debug("RICK_ROLLS")
        logger.debug(rick_rolls)
        logger.debug("REDIRECTS")
        logger.debug(redirects)
        if len(rick_rolls) > 1:
            urls = ""
            for url, info in rick_rolls.items():
                original = ", ".join(redirects[url])
                check = rick_rolls[url].check
                logger.debug(f"CHECK: {check}")
                if check == "domain":
                    urls += f"\n{original} -> {rick_rolls[url].extra}"
                elif check == "redirect":
                    urls += f"\n{original} -> {rick_rolls[url].extra}"
                elif original:
                    urls += f"\n{original} -> {url}"
                else:
                    urls += f"\n{url}"
            msg = f"**:warning: Detected Rickroll at {len(rick_rolls)} URLs:**```{urls}```"
            await message.channel.send(msg)
        else:
            url = list(rick_rolls.keys())[0]
            original = ", ".join(redirects[url])
            check = rick_rolls[url].check
            logger.debug(f"CHECK: {check}")
            if check == "domain":
                url = f"\n{original} -> {rick_rolls[url].extra}"
            elif check == "redirect":
                url = f"\n{original} -> {rick_rolls[url].extra}"
            elif original:
                url = f"\n{original} -> {url}"
            else:
                url = f"\n{url}"
            msg = f"**:warning: Detected Rickroll at URL:\n**```{url}```"
            await message.channel.send(msg)

    async def process_rick_rolls(self, message):
        """
        Calls find_rick_rolls, then processes results, sends a message if necessary and adds any rickrolls found to redis cache.
        Returns True or False depending on whether any rickrolls were found.
        :param message: discord Message object to be checked.
        :return: list of dicts, each with "is_rick_roll" and "extra" fields.
        """
        logger.debug(f"Checking message {message.id}.")

        if not self.stats:
            raise Exception("STATS NOT LOADED")

        self.stats.messages_seen += 1

        urls = self.get_urls(message.content)

        if not urls:
            return

        async with aiohttp.ClientSession() as session:
            detector = RickRollDetector(self, urls, session)
            rick_rolls, redirects = await detector.find_rick_rolls()

        self.stats.rickrolls_detected += len(rick_rolls)

        if not rick_rolls:
            return

        await self.process_results(message, rick_rolls, redirects)

        # write new rickrolls to Redis
        # todo: cache non-rick-rolls too
        for url, data in rick_rolls.items():
            if data.check != "redis":
                await self.redis.url_set(url, True, data.check, data.extra)
            for original_url in redirects[
                url
            ]:  # defaultdict so returns empty list if no associated redirects
                await self.redis.url_set(original_url, True, "redirect", url)

        return bool(rick_rolls)

    async def setup(self):
        self.session = aiohttp.ClientSession()
        for cog in self.properties.cogs:
            try:
                await self.load_extension(cog)
            except commands.ExtensionFailed as exception:
                traceback.print_exception(
                    type(exception), exception, exception.__traceback__
                )

    async def cleanup(self):
        await self.session.close()
