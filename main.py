from crawler import WebCrawler

# runner file

if __name__ == '__main__':
    # initiate a crawl, the crawler encapsulates the event loop
    c = WebCrawler('https://github.com')
    c.crawl()