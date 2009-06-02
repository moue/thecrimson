from django import template
from django.template.loader import render_to_string

register = template.Library()

class RotatorNode(template.Node):
    """
    Generates a rotator.  
    2 required arguments:
        @contents => list of content to rotate
        @id => unique (for the page) id.  used as 'id' attribute in html
    Optional:
        @title => a title (displayed at the top)
    """
    def __init__(self, contents, id, title=None):
        self.contents, self.id, self.title = contents, id, title
    
    def render(self, context):
        try:
            self.contents = self.contents.resolve(context, True)
        except:
            return ''
        try:
            self.title = self.title.resolve(context, True) if self.title else ''
        except:
            pass
        return render_to_string('templatetag/rotator.html', 
            {'contents': self.contents, 'title': self.title})
    

def do_rotator(parser, token):
    tokens = token.split_contents()
    if len(tokens) < 3:
        raise template.TemplateSyntaxError, \
            "%r tag takes at least 2 arguments" % tokens[0]
    contents = parser.compile_filter(tokens[1])
    id = tokens[2] if tokens[2][0] != '"' else tokens[2][1:-1]
    if len(tokens) > 3:
        title = tokens[3] if tokens[3][0] != '"' else tokens[3][1:-1]
    else:
        title = ''
    
    return RotatorNode(contents, id, title)

register.tag('rotator', do_rotator)