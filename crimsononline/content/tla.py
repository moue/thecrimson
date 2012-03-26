import json
import logging
import os
import urllib

try:
    import httplib2
except ImportError:
    print "httplib2 is available at http://tinyurl.com/6mpw2v"
    raise

__author__    = 'Ed Eliot'
__copyright__ = 'Copyright (c) 2009, Project Fondue'
__license__   = 'FreeBSD'
__version__   = '2.0.1'

TLA_URL = 'http://www.text-link-ads.com/xml.php?k=%s&l=python-tla-2.0.1&f=json'

HTTP_TIMEOUT = 5
HTTP_CACHE_FILENAME = '/tmp/tla.%s.json' # %s replaced with inventory key

LOG_FILENAME = '/tmp/tla.%s.log' # %s replaced with inventory key
LOG_LEVELS = {
    'debug': logging.DEBUG,
    'info': logging.INFO,
    'warning': logging.WARNING,
    'error': logging.ERROR,
    'critical': logging.CRITICAL
}
LOG_LEVEL = 'info'

MEMCACHE_ENABLED = False
CACHE_EXPIRY = 3600 # defaults to 1 hour
MEMCACHE_HOSTS = ('127.0.0.1:11211',)

if MEMCACHE_ENABLED:
    try:
        import memcache
    except ImportError:
        print "python-memcached is available at http://tinyurl.com/5agmel"
        raise

__all__ = ['TextLinkAds', '__version__']

class TextLinkAds:
    """library for returning and caching text link ads from TLA"""

    def __init__(self, inventory_key, **kwargs):
        """class constructor"""
        
        url = kwargs.get('url', TLA_URL)
       
        self.http_timeout = kwargs.get('http_timeout', HTTP_TIMEOUT)
        self.http_cache_filename = kwargs.get(
            'http_cache_filename', HTTP_CACHE_FILENAME
        ) % inventory_key
        
        self.log_filename = kwargs.get('log_filename', 
                                                LOG_FILENAME % inventory_key)
        self.log_levels = kwargs.get('log_levels', LOG_LEVELS)
        self.log_level = kwargs.get('log_level', LOG_LEVEL)
        self.logger = self.setup_logger()

        self.url = url % inventory_key
        
        self.caching_enabled = kwargs.get('caching_enabled', MEMCACHE_ENABLED)

        # instantiate memcache instance - if it fails disable using memcache 
        # and make a new request to TLA for each page view
        if self.caching_enabled:
            memcache_hosts = kwargs.get('memcache_hosts', MEMCACHE_HOSTS or [])
            self.memcache_expiry = kwargs.get('cache_expiry', CACHE_EXPIRY)
            self.memcache_key = 'tla%s' % inventory_key
            try:
                self.memcache = memcache.Client(memcache_hosts, debug=0)
                self.caching_enabled = True
            except ValueError, msg:
                self.caching_enabled = False
                self.logger.error(
                    'Incorrect memcache server format specifed (%s)' % (msg)
                )


    def setup_logger(self):
        """ set up logger to record errors to file """
        
        logger = logging.getLogger('TLA')
        logger.setLevel(self.log_levels[self.log_level])
        file_handle = logging.FileHandler(self.log_filename)
        file_handle.setLevel(self.log_levels[self.log_level])
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        file_handle.setFormatter(formatter)
        logger.addHandler(file_handle)
        return logger


    def write_http_cache(self, content):
        """ write response of http request to file """
        
        try:
            http_cache_file = open(self.http_cache_filename, 'w')
            http_cache_file.write(content)
            http_cache_file.close()

            return True
        except IOError, msg:
            self.logger.error(
                'Failed to write http cache file (%s)' % (msg)
            )


    def read_http_cache(self):
        """ read cached copy of last successful http request from file """
        
        if os.path.exists(self.http_cache_filename):
            try:
                http_cache_file = open(self.http_cache_filename, 'r')
                content = http_cache_file.read()
                http_cache_file.close()

                return content
            except IOError, msg:
                self.logger.error(
                    'Failed to read http cache file (%s)' % (msg)
                )


    def fetch(self):
        """make http request for TLA ads"""

        # no cache details specified as TLA doesn't seem to do anything 
        # with last modified or etag - it returns a 200 each time
        request = httplib2.Http(timeout=self.http_timeout)
        
        # httplib2 will return a status code instead of an exception on 
        # error - easier to handle when all we care about is whether or  
        # not we got a 200
        request.force_exception_to_status_code = True
        
        response, content = request.request(self.url)

        # anything but a 200 means data wasn't successfully retrieved
        if response.status == 200:
            # cache response in file in case of future failed requests
            self.write_http_cache(content)

            return content
        else:
            # http request failed, retrieve data from cache file if present
            return self.read_http_cache()


    def get_data(self):
        """Get a dictionary of raw data containing links from TLA"""
        
        if self.caching_enabled and self.memcache.get(self.memcache_key):
            return self.memcache.get(self.memcache_key)
        else:
            data = self.fetch()

            if data:
                links = json.loads(data)
                link_data = []
                
                # build list containing details of each ad
                for link in links:
                    link_data.append({
                        'url': link['URL'],
                        'text': link['Text'],
                        'beforeText': link['BeforeText'],
                        'afterText': link['AfterText']
                    })

                if self.caching_enabled:
                    self.memcache.set(
                        self.memcache_key, 
                        link_data, 
                        self.memcache_expiry
                    )

                return link_data

    def get_html(self, **kwargs):
        """get rendered list of links
        
        Optionally allows the user to pass in the following:

        header_level (1-6) -  The heading level to be displayed as html
        header_text - the text for the heading. (may contain html)
        
        class_attr - an optional classname for the ul
        id_attr - an optional id for the ul
        
        """
        links = self.get_data()

        if links:
            html = []

            header_level = kwargs.get('header_level')
            header_text  = kwargs.get('header_text')
            class_attr  = kwargs.get('class_attr')
            id_attr  = kwargs.get('id_attr')

            if header_level and header_text:
                if header_level not in range(1, 7):
                    raise ValueError, "HTML heading levels must be between 1-6"

                html.append('<h%s>%s</h%s>' % (
                    header_level, header_text, header_level)
                )
   
            
            class_attr = class_attr and " class='%s'" % class_attr or ''   
            id_attr = id_attr and " id='%s'" % id_attr or ''   

            html.append('<ul%s%s>' % (class_attr, id_attr))

            for link in links:
                if link['url'] and link['text']:
                    html.append(
                        '<li>%s<a href="%s">%s</a>%s</li>' % (
                            link['beforeText'], 
                            link['url'], 
                            link['text'], 
                            link['afterText'],
                        )
                    )

            html.append('</ul>')

            return '\n'.join(html)
