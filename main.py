from crawler import WebCrawler
import datetime

# runner file

if __name__ == '__main__':
    search_url = argv[1] or 'https://github.com'
    print('WebCrawler started, scanning {0}'.format(search_url))
    # initiate a crawl, the crawler encapsulates the event loop
    c = WebCrawler(search_url)
    c.crawl()
