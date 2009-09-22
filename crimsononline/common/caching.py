from hashlib import sha1
from django.core.cache import cache as _djcache
from django.http import HttpRequest
from django.utils.cache import get_cache_key

def funcache(seconds=1800, prefix=""):
    """Cache the result of a function call for the specified number of seconds.
   
    Usage:
    
    @cache(600)
    def myExpensiveMethod(parm1, parm2, parm3):
        ....
        return expensiveResult
    """
    def doCache(f):
        def x(*args, **kwargs):
            l = [f.__module__, getattr(f, 'im_class', ''), 
                 f.__name__, args, kwargs]
            key = sha1(''.join([str(x) for x in l])).hexdigest()
            result = _djcache.get(key)
            if result is None:
                result = f(*args, **kwargs)
                _djcache.set(key, result, seconds)
            return result
        
        return x
    
    return doCache

# Path is something like /section/fm/
def expire_page(path):
    request = HttpRequest()
    request.path = path
    key = get_cache_key(request)
    if _djcache.has_key(key):   
        _djcache.delete(key)
        
def expire_stuff():
    # EXPIRE ALL OF IT
    # always want to expire index
    expire_page('/')  
    print "Index expired"