import discord
from discord.ext import commands
from discord.ext import tasks

import signal
import asyncio
import datetime
import logging
import traceback
import aiohttp
import random
import sys

# custom imports
from utils.db import AsyncRedis
from utils import properties
import auth

logger = logging.getLogger('bot.astley')


class Astley(commands.AutoShardedBot):
    """
    Base class that hides stupid event loop and systemd stuff.
    """
    def __init__(self, *args, **kwargs):
        kwargs['command_prefix'] = properties.prefix
        kwargs['intents'] = discord.Intents(guild_messages=True, guilds=True)
        super().__init__(*args, **kwargs)
        self.loggers = dict()
        self._exit_code = 0
        self.started_at = datetime.datetime.now()
        self.redis = AsyncRedis()
        self.properties = properties
        self.session = aiohttp.ClientSession()

    async def try_run(self, coro):
        try:
            return await coro
        except:
            logger.error(f"Encountered error in try_run:", exc_info=True)
            return

    async def on_ready(self):
        """
        Override this to override discord.Client on_ready.
        """
        logger.info('Logged in as {0.user}.'.format(self))
        self.update_presence.start()
        logger.info('Bot is ready.')

    async def on_command_completion(self, ctx):
        logger.debug(f"Command '{ctx.command.qualified_name}' invoked by user {ctx.author.id} in channel {ctx.channel.id}, guild {ctx.guild.id}.")


    @tasks.loop(minutes=20)
    async def update_presence(self):
        activity = None
        name = random.choice(self.properties.activities)
        if name.lower().startswith("playing "):
            activity = discord.Game(name.replace("playing ", ""))
        elif name.lower().startswith("watching "):
            activity = discord.Activity(type=discord.ActivityType.watching,
                                        name=name.replace("watching", ""))
        elif name.lower().startswith("listening to "):
            activity = discord.Activity(type=discord.ActivityType.listening,
                                        name=name.replace("listening to ", ""))
        if activity:
            await self.change_presence(activity=activity)

    async def setup(self):
        """
        Called when bot is started, before login.
        Use this for any async tasks to be performed before the bot starts.
        (THE BOT WILL NOT BE LOGGED IN WHEN THIS IS CALLED)
        """
        pass

    async def cleanup(self):
        """
        Called when bot is closed, before logging out.
        Use this for any async tasks to be performed before the bot exits.
        """
        pass

    def run(self, bot, token=None, *args, **kwargs):
        logger.debug("Run method called.")
        token = token if token else (
            auth.DISCORD_TOKEN if bot == 'main'
            else auth.DISCORD_DEV_BOT_TOKEN)
        super().run(token, *args, **kwargs)

    async def start(self, *args, **kwargs):
        logger.debug("Start method called.")
        try:
            self.loop.remove_signal_handler(signal.SIGINT)
            self.loop.add_signal_handler(signal.SIGINT, lambda: asyncio.create_task(self.close()))
        except NotImplementedError:
            pass
        logger.info("Setting up.")
        await self.setup()
        logger.debug("Setup complete.")
        logger.debug("Calling super().start method.")
        await super().start(*args, **kwargs)

    async def close(self, exit_code=0):
        logger.debug("Astley: received command to shut down. Beginning safe shutdown sequence.")
        self._exit_code = exit_code
        await self.cleanup()
        logger.debug("Closing connection to discord.")
        await super().close()

    async def on_error(self, event_method, *args, **kwargs):
        exc = traceback.format_exc()
        logger.error(f"Ignoring exception in {event_method}:\n{exc}")
        hook = discord.Webhook.from_url(auth.WEBHOOKS['errors'], adapter=discord.AsyncWebhookAdapter(self.session))
        try:
            await hook.send(f"Exception occurred in {event_method}: ```py\n{exc[:1850]}\n```")
        except discord.DiscordException:
            logger.error("Failed to log error to logging channel.")

    async def on_command_error(self, context, exception):
        exc = traceback.format_exception(exception.__class__, exception, exception.__traceback__)
        exc = ''.join(exc) if isinstance(exc, list) else exc
        logger.error(f'Ignoring exception in command {context.command}:\n{exc}')
        if not context.command or isinstance(exception, commands.UserInputError):
            return
        hook = discord.Webhook.from_url(auth.WEBHOOKS['errors'], adapter=discord.AsyncWebhookAdapter(self.session))
        try:
            await hook.send(f"Exception occurred in command {context.command}: ```py\n{exc[:1850]}\n```")
        except discord.DiscordException:
            logger.error("Failed to log error to logging channel.")




