
import multiprocessing
import asyncio
import time
import enum

from utils.helpers import setup_logger
from utils.helpers import maybe_coroutine


logger = setup_logger("scanner")
POOL_SIZE = 1
DEFAULT_TIMEOUT = 5


class ScanResults(enum.Enum):
    """
    Possible results of scan() in place of confidence rating.
    """
    check_failed = "Check returned false, scan function was not run."
    timed_out = "The scan took too long to complete and is no longer being watched."


class Scanner:
    def __init__(self, pool_size=POOL_SIZE, timeout=DEFAULT_TIMEOUT):
        self.timeout = timeout
        self.unretrieved_results = list()
        self.pool = multiprocessing.Pool(processes=pool_size)

    def scanner(self, *args, **kwargs):
        """
        Method that should actually be run to determine if there's a suspected Rick roll.
        Should return float representing confidence value.

        Can be either a coroutine or a regular function.

        :rtype: float
        """

    def check(self, *args, **kwargs):
        """
        Checks whether a scan is necessary.
        Should be used to prevent unnecessary tasks being added to the worker processes

        Can be either a coroutine or a regular function.

        :rtype: bool
        """

    def reformat(self, *args, **kwargs):
        """
        Takes in data about the message and returns args and kwargs for scanner(), if necessary.
        Should return a list of args and a dict of kwargs.
        """
        return args, kwargs

    async def scan(self, *args, **kwargs):
        """
        Runs the scanner function and returns the result.
        Input should be input designated for reformat() if implemented.
        Otherwise, treat it as if scanner() is being run directly

        Will return either a float or a ScanResult.
        """
        if await maybe_coroutine(self.check, *args, **kwargs):
            args, kwargs = await maybe_coroutine(self.reformat, *args, **kwargs)
            return await self.run_process(args, kwargs)
        else:
            # if the check fails
            return ScanResults.check_failed

    async def run_process(self, args, kwargs):

        # send data to multiprocessing pool
        if asyncio.iscoroutinefunction(self.scanner):
            coro = self.scanner(*args, **kwargs)
            result = self.pool.apply_async(asyncio.run, coro)
            # maybe_coroutine is not used here to prevent unnecessary calls to asyncio.run
        else:
            result = self.pool.apply_async(self.scanner, args, kwargs)

        # wait for result
        t = time.monotonic()
        while time.monotonic() - t < self.timeout:
            if result.ready():
                return result.get()

        # if it times out before returning a result
        self.unretrieved_results.append(result)
        return ScanResults.timed_out
