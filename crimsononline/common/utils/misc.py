from django.conf import settings

def static_content(link):
    """ 
    returns a url to a piece of static content relative to the static folder
    """
    return settings.MEDIA_URL + link

def ret_on_fail(fn, retval, exception_tuple=Exception):
    """Function modifier to return retval if an exception is thrown.
    
    Does not work well as a decorator, cause I'm not that 1337.
    
    Only gives retval if the exception is in exception_tuple, 
    otherwise, reraises the exception.
    """
    def fn_prime(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except exception_tuple:
            return retval
        except:
            raise
    return fn_prime
