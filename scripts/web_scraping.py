
import requests
from bs4 import BeautifulSoup


class YouTubeClient:

    def get_page(self, url):
        response = requests.get(url)
        return response.text

    def get_page_info(self, html):
        soup = BeautifulSoup(html, features="html.parser")
        with open('rick.html', 'w') as f:
            f.write(soup.prettify())
        print(soup.head.title.text)
        result = soup.find(id='eow-description')
        print(result.text)
        result = soup.find(id='eow-title')
        print(result.text)
        result = soup.find(id='eow-comments')
        print(result.text)


def main():
    client = YouTubeClient()
    html = client.get_page('https://www.youtube.com/watch?v=kR0gOEyK6Tg')
    client.get_page_info(html)


if __name__ == "__main__":
    main()

