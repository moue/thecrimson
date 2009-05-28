import string

IDENTITY_TRANS = string.maketrans("","")
def alphanum_only(s):
    """ strips punctuation. see http://stackoverflow.com/questions/265960/"""
    s = s.encode('ascii', 'ignore')
    return s.translate(IDENTITY_TRANS, string.punctuation)

URL_SAFE = string.letters + string.digits + '._-'
def make_url_friendly(s):
    """
    kills non alpha numeric chars and replaces spaces with underscores
    """
    # TODO: THIS IS BACKWARDS
    return s.translate(IDENTITY_TRANS, URL_SAFE)
    
def make_file_friendly(str):
    return make_url_friendly(str)
    
def strip_commas(s):
    if s:
        s = s.replace(',,', ',')
        s = s[1:] if s[0] == ',' else s
    if s:
        s = s[:-1] if s[-1] == ',' else s
    return s