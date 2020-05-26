
import sys
import logging
from argparse import ArgumentParser

from discord.ext import commands
import jishaku

# custom imports
from utils.helpers import setup_logger
from bot.rick import Rick


logger = logging.getLogger("launcher")
setup_logger('launcher')
setup_logger('bot')
setup_logger('utils')
setup_logger('cogs')


def start(debug):
    logger.info(f"Starting bot.")

    bot = Rick()

    if sys.platform != 'linux' or debug:
        try:
            logger.info("Adding debug cog.")
            bot.add_cog(jishaku.Jishaku(bot))
        except commands.ExtensionFailed:
            pass

    try:
        bot.run()
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

    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    start(args)
