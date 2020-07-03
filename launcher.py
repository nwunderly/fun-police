
import sys
import logging
from argparse import ArgumentParser

from discord.ext import commands

# custom imports
from utils.helpers import setup_logger
from bot.rick import Rick


logger = logging.getLogger("launcher")


def start(_args):
    debug = _args.debug
    dev_bot = _args.dev_bot

    setup_logger('launcher', debug)
    setup_logger('bot', debug)
    setup_logger('utils', debug)
    setup_logger('cogs', debug)
    setup_logger('discord', False)


    logger.info(f"Starting bot.")

    bot = Rick()

    # if sys.platform != 'linux' or debug:
    try:
        logger.info("Adding debug cog.")
        bot.load_extension('jishaku')
    except commands.ExtensionFailed:
        pass

    try:
        bot.run(bot=('main' if not dev_bot else 'dev'))
    finally:
        try:
            exit_code = bot._exit_code
        except:
            logger.info("Bot's exit code could not be retrieved.")
            exit_code = 0
        logger.info(f"Bot closed with exit code {exit_code}.")
        exit(exit_code)


def parse_args():

    parser = ArgumentParser(description="Start Rickroll Detector bot.")
    parser.add_argument('--debug', '-d', action='store_true')
    parser.add_argument('--dev-bot', '-dev', action='store_true')

    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    start(args)
