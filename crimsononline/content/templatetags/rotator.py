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
    def __init__(self, contents, id, title, nopreview, wide):
        self.contents, self.id, self.title = contents, id, title
        self.nopreview = nopreview
        self.wide = wide
    
    def render(self, context):
        try:
            self.contents = self.contents.resolve(context, True)
        except:
            return ''
        try:
            self.title = self.title.resolve(context, True) if self.title else ''
        except:
            self.title = ''
        return render_to_string('templatetag/rotator.html', 
            {'contents': self.contents, 'title': self.title, 
             'nopreview': self.nopreview, 'id': self.id, 'wide': self.wide})
    

def do_rotator(parser, token, nopreview=False, wide=False):
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
    
    return RotatorNode(contents, id, title, nopreview, wide)

def do_rotator_np(parser, token):
    return do_rotator(parser, token, True)
    
def do_rotator_w(parser, token):
    return do_rotator(parser, token, nopreview=False, wide=True)

def do_rotator_np_w(parser, token):
    return do_rotator(parser, token, nopreview=True, wide=True)
    
register.tag('rotator', do_rotator)
register.tag('rotatornopreview', do_rotator_np)
register.tag('rotatorwide', do_rotator_w)
register.tag('rotatornopreviewwide', do_rotator_np_w)