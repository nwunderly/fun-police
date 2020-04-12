
# custom imports
from utils.helpers import setup_logger
from bot.backend import Astley
from scanners.scanner import ScanResults
from scanners import urlchecker


logger = setup_logger("Rick")


class Rick(Astley):
    """
    A bot that detects and warns you about possible Rick rolls.
    """
    def __init__(self):
        super().__init__(command_prefix="rr!")
        self.scanners = list()

    async def on_message(self, message):
        if message.author == self.user:
            return
        if not message.guild:
            await self.process_private_messages(message)
        else:
            await self.process_commands(message)
            if message.channel.category.id != 577706266768703488 and message.channel.id != 671418412127355040:
                return  # todo remove this later
            await self.process_rick_rolls(message)

    async def process_private_messages(self, message):
        msg = f"Received private message from {message.author} ({message.author.id}) - {message.clean_content}"
        logger.info(msg)
        await self.get_channel(0).send(msg)

    async def process_rick_rolls(self, message):
        logger.debug(f"Checking message {message.id}.")
        results = dict()
        for scanner in self.scanners:
            result = await scanner.scan(message)
            results[scanner.name] = result
        if await self.process_results(results):
            s = f"Url in the previous message triggered the following scanners:"
            for key, value in results.items():
                if isinstance(value, ScanResults) or value > 0:
                    s += f"\n{key}: {value}"
            await message.channel.send(s)
        else:
            logger.debug(f"Nothing of note found in message {message.id}.")

    async def process_results(self, results):
        """
        Results will be a dict of scanner names mapped to floats.
        This function will process overall results and make the final judgement.
        """
        for key, value in results.items():
            if value > 0:
                return True
        return False

    async def setup(self):
        self.scanners.append(urlchecker.URLChecker())



