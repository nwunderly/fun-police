
from urllib.parse import urlparse, parse_qs
import re


def strip_url(url):
    url = url if (url.startswith('https://') or url.startswith('http://')) else 'http://' + url
    parsed = urlparse(url)

    def remove_www():
        match = re.match(r"(?:www\.)?(.*)", parsed.netloc)
        if match:
            netloc = match.group(1)
        else:
            netloc = parsed.netloc
        print(netloc)
        print(parsed.path)
        print(f"{netloc}/{parsed.path}?{parsed.query}")
        return f"{netloc}/{parsed.path}?{parsed.query}"

    # reassembles youtube address without unnecessary queries
    if parsed.netloc == 'www.youtube.com' or parsed.netloc == 'youtube.com':
        v = parse_qs(parsed.query).get('v')[0]
        if v:
            return f"youtube.com/watch?v={v}"

    # youtu.be -> youtube so it doesn't have to be resolved
    elif parsed.netloc == 'youtu.be':
        v = parsed.path[1:]
        if v:
            return f"youtube.com/watch?v={v}"

    # remove www. from misc URLs
    return remove_www()


print(strip_url('youtu.be/dQw4w9WgXcQ'))

