from django import template
from django.template.loader import render_to_string

register = template.Library()

class RotatorNode(template.Node):
    """
    Generates a rotator.  
    2 required arguments:
        @contents => list of content to rotate
        @id => unique (for the page) id.  used as 'id' attribute in html
    """
    def __init__(self, contents, id):
        print contents
        self.contents, self.id = contents, id
    
    def render(self, context):
        try:
            self.contents = self.contents.resolve(context, True)
            print self.contents
        except:
            raise
            return ''
        return render_to_string('templatetag/rotator.html', 
            {'contents': self.contents})
    

def do_rotator(parser, token):
    tokens = token.split_contents()
    if len(tokens) < 3:
        raise template.TemplateSyntaxError, \
            "%r tag takes 2 arguments" % tokens[0]
    contents = parser.compile_filter(tokens[1])
    id = tokens[2]
    
    return RotatorNode(contents, id)

register.tag('rotator', do_rotator)