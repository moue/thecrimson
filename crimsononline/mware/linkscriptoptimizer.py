import re

# Uses regular expressions to place link and script tags in the correct place
class LinkScriptOptimizer(object):
    def process_response(self, request, response):
        # only process if we have an html file
        if(re.compile("</head>").search(response.content) == None):
            return(response)
        
        # filters a regular expression from html, returning (stripped html, concatenated tags)
        def filterre(regexp, string):
            curend = 0
            matches = regexp.findall(string)
            if(len(list(matches))==0):
                return((string,""))
            tags = ""
            for match in matches:
                tags = tags + match
            return((regexp.sub("",string),tags))

        # moves tags matching regexp in front of given tag in given source
        def movetags(source, infrontof, regexp):
            curaddon = ""
            res = filterre(re.compile(regexp, re.DOTALL), source)
            curfiltered = res[0]
           
            curaddon = curaddon + res[1]

            ifoloc = re.compile(infrontof).search(curfiltered).start()            
            return(curfiltered[0:(ifoloc-1)] + curaddon + curfiltered[ifoloc:(len(curfiltered)-1)])
        
        # move css
        response.content = movetags(response.content, "</head>", "<link.*?/>")
        # move script tags
        response.content = movetags(response.content, "</body>", "<script.*?>.*?</script>")
        return(response);
