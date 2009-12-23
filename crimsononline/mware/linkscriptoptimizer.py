import re
from crimsononline.common.utils import lists

# Uses regular expressions to place link and script tags in the correct place
# TODO: cache the compiled REs to make it go a bit faster


def filterre(regexp, str):
    """Filters regexp from str, result and what was filtered out.
    
    returns (filtered str, [match0, match1, ...])
    """
    matches = regexp.findall(str)
    if matches is None:
        return (str, [])
    return (regexp.sub('', str), matches)

SCRIPT_RE = re.compile(r'<script.*?>.*?</script>', re.DOTALL)
LINK_RE = re.compile(r'<link.*?/>', re.DOTALL)
def movetags(source, infrontof, regexp):
    filtered, tags = filterre(regexp, source)
    tags = '\n'.join(lists.uniquify(tags))
    return filtered.replace(infrontof, tags + infrontof, 1)

class LinkScriptOptimizer(object):
    """Put <link> and <script> tags in the right place.
    
    Removes duplicate script / link inclusions, cause Django is fucking dumb.
    Moves <link>s to the head, moves <scripts> to right before </body>.
    """
    def process_response(self, request, response):
        # ignore non html pages, non admin pages (cause I'm too lazy to test)
        if not request.path.startswith('/admin') or \
            not response.get('Content-Type', '').startswith('text/html') or \
            request.GET.get('nolso', False):
            return response
        
        # move css
        response.content = movetags(response.content, "</head>", LINK_RE)
        # move script tags
        response.content = movetags(response.content, "</body>", SCRIPT_RE)
        return response
