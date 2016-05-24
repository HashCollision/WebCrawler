# -*- coding: utf-8 -*-
# deps
import asyncio, aiohttp, re, json, threading, time, sys
from bs4 import BeautifulSoup as soup
from asyncio import Queue
from datetime import datetime

class WebCrawler:
    '''
        WebCrawler class, starts at a root domain of a given resource.
    
        It starts on the root page, finds all 
    
        Initialize a new webcrawler instance.
        
        @param(basePath): The root of the domain to crawl 
        
    '''
    def __init__(self, basePath, max_tasks=25):
        
        # max concurrent tasks
        self.max_tasks = max_tasks
        
        # we have seen this url
        self.processed = set()
        
        # BasePath of url to start crawl, should be root of a domain 
        self.basePath = basePath
        
        # event loop, we are not fallbacking to iocp (win32) or select or any sort of other event loop, we will only use asyncio provided event loop
        self.loop = asyncio.get_event_loop()
        
        # create our session, which encapsulates a connection pool
        self.session = aiohttp.ClientSession(loop=self.loop)
        
        # get Queue
        self.queue = Queue(loop=self.loop)
        
        # first url
        self.queue.put_nowait(self.basePath)
        
        # JSON for visualization
        self.data = []
        
    
    '''
        Check if this is static data
    '''
    def _is_static_(self):
        # As far as static vs. dynamic, it's because it looks like the resource is cachable (making it "static"). 
        # You need a pragma: no-cache and/or a cache-control: no-cache header for it to really be a dynamic asset.
        pass
        
        
    '''
        Get all static assets on a page
    '''
    def get_static(self, s, url):
        # hacky but works
        scripts = [ x['src'] for x in s.findAll('script') if x.has_attr('src') and (x["src"].startswith('/') and not x['src'][1] == '/')]
        styles = [ x['href'] for x in s.findAll('link') if x.has_attr('href') and x["href"].startswith('/') ]
        return scripts + styles
        
    '''
        Cleanup on aiohttp
    '''
    def close(self):
        try:
            # aiohttp keeps a TCP connection alive for 30secs, this explicitly closes it
            self.session.close()
        except:
            pass
  
    '''
        Process is a coroutine which our tasks/workers/threads/coroutines/whatever will do their corresponding work.
        Each process will fetch their urls from the queue for processing.
    '''
    async def process(self):
        try:
            while True:
                try:
                    # suspend until we get a new url to work on
                    url = await self.queue.get()
                    
                    # remove trailing slash
                    if url[-1] == '/':
                        url = url[:-1]
                    
                    # we have not seen this url, so we fetch it and add it
                    if url not in self.processed:
                        self.processed.add(url)
                        
                        # suspend execution until we get data from our HTTP request
                        resp = await self.fetch(url)
                        
                        if resp != None:
                            # add to sites
                            self.data.append(resp)
                        
                            # go through each link and add them to the queue if we have not traversed them
                            links = [x for x in resp['links'] if x.startswith('/') or x.startswith(url)]
                            for link in links:
                                
                                # formatting
                                if not link.startswith(self.basePath):
                                    link = self.basePath + link
                                
                                if '#' in link:
                                    link = link[:link.index('#')]
                                
                                # add it to our queue for processing
                                if link not in self.processed:
                                    if link != '' and link != None:
                                        self.queue.put_nowait(link)
                                    
                    # this task is done
                    self.queue.task_done()
                    
                            
                        
                except Exception as err:
                    pass
                    
        except asyncio.CancelledError:
            pass
  
    
    '''
        Parsed a url for links and other stuff too
    '''
    def parse(self, data, url):
        # parse a single url
        s = soup(data.decode('utf-8', 'ignore'), "html.parser")
        
        # get links
        links = [ x['href'] for x in s.findAll('a') if x.has_attr('href') ]
        
        # get assets 
        assets = self.get_static(s, url)
        
        # get title
        title = s.find('title')
        
        if title != None:
            title = title.text
        else:
            title = ''
            
        return {
            'url': url,
            'title': title,
            'links': links,
            'assets': assets
        }
    

    '''
        Put our JSONStatham in a file
    '''
    def _save_file(self):

        # save data
        with open('sitemap.json', 'w') as sitemapfile:
            json.dump({
                "sitemap": "Sitemap generated for URL {} on {}. {} pages parsed.".format(self.basePath, datetime.now(), len(self.processed)),
                "sites": self.data
            }, sitemapfile)
    
    
    '''
        Start ze crawl
    '''
    def crawl(self):
        try:
            # crawl until complete
            self.loop.run_until_complete(self.__crawl__())
            
        except KeyboardInterrupt:
            sys.stderr.flush()
        finally:
            pass
            

  
    '''
        Asynchronous crawl
    '''
    async def __crawl__(self):
        print('Starting webcrawler on url {}'.format(self.basePath))
        
        t1 = time.time()
        # make tasks that are processing the queue
        tasks = [asyncio.ensure_future(self.process(), loop=self.loop) for _ in range(self.max_tasks)]
        
        # aggregate tasks and squash exceptions
        asyncio.gather(*tasks, return_exceptions=True)
        
        # all queue items should call task_done for each put
        await self.queue.join()
        
        # cancel tasks
        for t in tasks:
             t.cancel()
        
        self.close()
        self.loop.stop()
        
        # save JSON file for viewing
        self._save_file()
        
        # 
        print('{} pages processed in {} secs. Data saved in sitemap.json'.format(len(self.processed), time.time() - t1))
        
        # leave
        exit(1)

    '''
        HTTP request a page.
    '''         
    async def fetch(self, url):
        try:
                
            # alright, so i really should be handling redirects myself, but i'm not, because of reasons
            async with self.session.get(url, allow_redirects=False) as r:
                assert r.status == 200
                # Get the page and parse it
                resp = self.parse(await r.read(), url)    
                return resp
        except:
            self.queue.task_done()
            
        
            
            
