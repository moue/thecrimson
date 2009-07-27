from hashlib import sha1
from django.core.cache import cache as _djcache

def funcache(seconds=1800):
    """Cache the result of a function call for the specified number of seconds
    
    Uses Django's caching mechanism, and assumes that
    the function's result depends only on its parameters.
    
    Note that the ordering of parameters is important. 
    e.g. myFunction(x = 1, y = 2), myFunction(y = 2, x = 1), 
    and myFunction(1,2) will each be cached separately. 
    
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
