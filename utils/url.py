import logging

from utils.helpers import get_domain, strip_url

logger = logging.getLogger("utils.url")


class QuestionableURL:
    """
    A single possible Rick Roll URL.
    Stores useful info about a particular URL as it progresses through the checks.
    """

    def __init__(self, url):
        self._original_url = url
        self._original_domain = get_domain(url)
        self._stripped_original_url = strip_url(url)
        self._resolved_url = None
        self._resolved_domain = None
        self._stripped_resolved_url = None
        self.response = None
        self._closed = False

    def url(self, stripped=True):
        if self._closed:
            raise ValueError("URL is closed.")
        if stripped:
            if self._stripped_resolved_url:
                return self._stripped_resolved_url
            else:
                return self._stripped_original_url
        else:
            if self._resolved_url:
                return self._resolved_url
            else:
                return self._original_url

    def domain(self):
        if self._resolved_domain:
            return self._resolved_domain
        else:
            return self._original_domain

    def update(self, url):
        if self._closed:
            raise ValueError("URL is closed.")
        if self._resolved_url:
            raise ValueError("This URL has already been updated.")
        resolved = url
        self._resolved_url = resolved
        self._resolved_domain = get_domain(resolved)
        self._stripped_resolved_url = strip_url(resolved)

    async def read(self, size=None):
        if self.response:
            if size:
                return (await self.response.read(size)).decode()
            else:
                return (await self.response.read()).decode()
        else:
            raise ValueError(
                "URL has not been updated with a response and cannot be read."
            )

    def close(self):
        self._closed = True
        if self.response:
            # await self.response.release()
            self.response.close()
