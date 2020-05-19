from discord.ext import commands
from discord.ext import tasks

import signal
import asyncio
import datetime
import sdnotify

# custom imports
from utils.db import AsyncRedis
from utils.helpers import setup_logger
from confidential import authentication

logger = setup_logger("Astley")


class Astley(commands.AutoShardedBot):
    """
    Base class that handles backend event loop stuff
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.loggers = dict()
        self._exit_code = 0
        self._sd_notifier = sdnotify.SystemdNotifier()
        self.sd_ready()
        self.started_at = datetime.datetime.now()
        self.redis = AsyncRedis()
        logger.debug(f"Initialization complete.")

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

    async def on_command_completion(self, ctx):
        logger.info(f"Command '{ctx.command.qualified_name}' invoked by user {ctx.author.id} in channel {ctx.channel.id}, guild {ctx.guild.id}.")

    def sd_notify(self, text):
        logger.debug(f"Sending sd_notify: {text}")
        self._sd_notifier.notify(text)

    def sd_ready(self):
        self.sd_notify("READY=1")
        self.sd_notify("WATCHDOG=1")

    @tasks.loop(seconds=1)
    async def sd_watchdog(self):
        self.sd_notify("WATCHDOG=1")

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

    def run(self, token=None, *args, **kwargs):
        logger.debug("Run method called.")
        token = token if token else authentication.DISCORD_TOKEN
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
