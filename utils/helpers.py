
import logging
import datetime
import sys
import asyncio
import re

logger = logging.getLogger('utils.helpers')


def setup_logger(name):
    logger = logging.getLogger(name)
    d = datetime.datetime.now()
    time = f"{d.month}-{d.day}_{d.hour}h{d.minute}m"

    if sys.platform == 'linux':
        filename = '/home/rick/logs/{}.log'
        level = logging.INFO
    else:
        filename = './logs/{}.log'
        level = logging.DEBUG

    file_handler = logging.FileHandler(filename.format(time))
    # file_handler.setLevel(level)

    stream_handler = logging.StreamHandler(sys.stdout)
    # stream_handler.setLevel(level)

    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    stream_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)
    logger.setLevel(level)
    return logger


async def maybe_coroutine(func, *args, **kwargs):
    if asyncio.iscoroutinefunction(func):
        return await func(*args, **kwargs)
    else:
        return func(*args, **kwargs)


def strip_url(url):
    url = url if isinstance(url, str) else url.human_repr()
    www = re.sub('https?://www\.', '', url)
    url = www if www else "www." + re.sub('https?://', '', url)
    url = re.sub('&feature=youtu.be', '', url)
    url = re.sub('&t=\d+', '', url)
    return url


