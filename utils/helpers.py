import asyncio
import datetime
import logging
import re
import sys
from urllib.parse import parse_qs, urlparse

import yarl

logger = logging.getLogger("utils.helpers")


def setup_logger(name, debug):
    _logger = logging.getLogger(name)
    d = datetime.datetime.now()
    time = f"{d.month}-{d.day}_{d.hour}h{d.minute}m"

    filename = "./logs/{}.log"
    if debug:
        level = logging.DEBUG
    else:
        level = logging.INFO

    file_handler = logging.FileHandler(filename.format(time))
    # file_handler.setLevel(level)

    stream_handler = logging.StreamHandler(sys.stdout)
    # stream_handler.setLevel(level)

    file_handler.setFormatter(
        logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    )
    stream_handler.setFormatter(
        logging.Formatter("%(name)s - %(levelname)s - %(message)s")
    )

    _logger.addHandler(file_handler)
    _logger.addHandler(stream_handler)
    _logger.setLevel(level)
    return _logger


async def maybe_coroutine(func, *args, **kwargs):
    if asyncio.iscoroutinefunction(func):
        return await func(*args, **kwargs)
    else:
        return func(*args, **kwargs)


def strip_url(url):
    if not url:
        return None
    if isinstance(url, yarl.URL):
        url = url.human_repr()
    url = (
        url
        if (url.startswith("https://") or url.startswith("http://"))
        else "http://" + url
    )
    parsed = urlparse(url)

    def remove_www():
        match = re.match(r"(?:www\.)?(.*)", parsed.netloc)
        if match:
            netloc = match.group(1)
        else:
            netloc = parsed.netloc
        _url = f"{netloc}"
        _url += f"{parsed.path}" if parsed.path else ""
        _url += f"{parsed.query}" if parsed.query else ""
        return _url

    # reassembles youtube address without unnecessary queries
    if parsed.netloc == "www.youtube.com" or parsed.netloc == "youtube.com":
        v = parse_qs(parsed.query)
        if v:
            v = v.get("v")
            if v:
                v = v[0]
                if v:
                    return f"youtube.com/watch?v={v}"

    # youtu.be -> youtube so it doesn't have to be resolved
    elif parsed.netloc == "youtu.be":
        v = parsed.path[1:]
        if v:
            return f"youtube.com/watch?v={v}"

    # remove www. from misc URLs
    return remove_www()


def get_domain(url):
    url = (
        url
        if (url.startswith("https://") or url.startswith("http://"))
        else "http://" + url
    )
    parsed = urlparse(url)
    return parsed.netloc
