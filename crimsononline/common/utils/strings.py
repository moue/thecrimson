import string
from random import choice
from django.template.defaultfilters import slugify

IDENTITY_TRANS = string.maketrans("","")
def alphanum_only(s):
    """ strips punctuation. see http://stackoverflow.com/questions/265960/"""
    s = s.encode('ascii', 'ignore')
    return s.translate(IDENTITY_TRANS, string.punctuation)

ALPHANUM = string.letters + string.digits
URL_SAFE = ALPHANUM + '._-'
def make_url_friendly(s):
    """
    kills non alpha numeric chars and replaces spaces with underscores
    """
    return slugify(s)
    
def make_file_friendly(str):
    return slugify(str)

def strip_commas(s):
    if s:
        s = s.replace(',,', ',')
        s = s[1:] if s[0] == ',' else s
    if s:
        s = s[:-1] if s[-1] == ',' else s
    return s

def rand_str(n):
    """random string of length n"""
    return ''.join([choice(ALPHANUM) for i in range(n)])
