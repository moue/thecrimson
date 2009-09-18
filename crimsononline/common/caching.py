from hashlib import sha1
from django.core.cache import cache as _djcache
from django.http import HttpRequest
from django.utils.cache import get_cache_key

def funcache(seconds=1800, prefix=""):
    """Cache the result of a function call for the specified number of seconds,
    using the specified prefix in the cache key for easy expiry
    TODO: Prefixes should probably be structured hierarchically, e.g.
          general_writer_juneqwu...
          so that we can expire the prefix general to expire everything, general_writer
          to expire all writers, and general_writer_juneqwu to expire just June's.
          But how can we write other modules such that we can pass this information to the cache...?
    
    Uses Django's caching mechanism, and assumes that
    the function's result depends only on its parameters.
    
    Note that the ordering of parameters is important. 
    e.g. myFunction(x = 1, y = 2), myFunction(y = 2, x = 1), 
    and myFunction(1,2) will each be cached separately. 
    
    Usage:
    
    @cache(600, 'expensive')
    def myExpensiveMethod(parm1, parm2, parm3):
        ....
        return expensiveResult
    """
    def doCache(f):
        def x(*args, **kwargs):
            l = [f.__module__, getattr(f, 'im_class', ''), 
                 f.__name__, args, kwargs]
            key = prefix + sha1(''.join([str(x) for x in l])).hexdigest()
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
        
#def expire_stuff(path):
    # EXPIRE ALL OF IT
    # always want to expire index
    # obviously always expire the path passed
    # we should expire the section pag 
