# custom imports
from utils.loggers import setup_logger
from bot.backend import Astley

logger = setup_logger("richard")


class Richard(Astley):
    """
    A bot that detects and warns you about possible Rick rolls.
    """
    def __init__(self):
        super().__init__(command_prefix="rr!")

    # todo implement interface with scanners in this class





