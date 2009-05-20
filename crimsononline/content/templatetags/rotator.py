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
        try:
            self.contents = template.Variable(contents)
        except:
            self.contents = None
        self.id = id
    
    def render(self, context):
        if self.contents is None:
            return ''
        return render_to_string('templatetag/rotator.html', 
            {'contents': self.contents})