import re
from crimsononline.common.utils import lists

# Uses regular expressions to place link and script tags in the correct place
# TODO: cache the compiled REs to make it go a bit faster
class LinkScriptOptimizer(object):
    def process_response(self, request, response):
        # only process if we have an html file
        if response.content.find('<html') < 0:
            return(response)
        
        # filters a regular expression from html, returning 
        #  (stripped html, concatenated tags)
        def filterre(regexp, string):
            matches = regexp.findall(string)
            if not matches:
                return (string, "")
            tags = '\n'.join(lists.uniquify(matches))
            return (regexp.sub("", string), tags)

        # moves tags matching regexp in front of given tag in given source
        def movetags(source, infrontof, regexp):
            res = filterre(re.compile(regexp, re.DOTALL), source)
            curfiltered, curaddon = res
            
            return curfiltered.replace(infrontof, curaddon + infrontof)
        
        # move css
        response.content = movetags(response.content, "</head>", "<link.*?/>")
        # move script tags
        response.content = movetags(response.content, 
            "</body>", "<script.*?>.*?</script>")
        return(response);
