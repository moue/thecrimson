import string

URL_SAFE = string.letters + string.digits + '._'
def make_url_friendly(str):
    """
    kills non alpha numeric chars and replaces spaces with underscores
    """
    str = str.replace(' ', '_')
    return ''.join([c for c in str if c in URL_SAFE])
    
def make_file_friendly(str):
    return make_url_friendly(str)
    
SLUG_SAFE = string.letters + string.digits + '-'
def make_slug(str):
    str = str.replace(' ', '-')
    return ''.join([c for c in str if c in SLUG_SAFE])