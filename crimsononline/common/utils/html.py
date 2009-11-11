import re

PARA_RE = re.compile(r'</p>\s*<p')
def para_list(s):
    """Split s on <p> tags
    
    Keep the <p> tags in the output.
    """
    # remove whitespace between adjacent tags, replace with sentinel value
    s = PARA_RE.sub('</p>,,,<p', s)
    # split by sentinel value
    return s.split(',,,')
