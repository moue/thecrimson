from django import template
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe

register = template.Library()

class ModuleNode(template.Node):
    """
    Generates a rotator.  
    2 required arguments:
        @contents => list of content to rotate
        @id => unique (for the page) id.  used as 'id' attribute in html
    Optional:
        @title => a title (displayed at the top)
    """
    def __init__(self, nodelist, title, width, color):
        self.nodelist, self.title, self.width, self.color = nodelist, title.upper(), width, color
    
    def __iter__(self):
        for node in self.nodelist:
            yield node
    
    def render(self, context):
        cont = mark_safe(self.nodelist.render(context))
        return render_to_string("templatetag/module.html",
            {'c':cont, 'title':self.title, 'width':self.width,'color':self.color})

def do_module(parser, token):
    tokens = token.split_contents()
    if len(tokens) < 3:
        raise template.TemplateSyntaxError, \
            '%r tag takes at least 3 arguments' % tokens[0]
    width = tokens[1]
    title = tokens[2] if tokens[2][0] not in ("'",'"') else tokens[2][1:len(tokens[2])-1]
    color = tokens[3] if len(tokens) == 4 else "blue"
    nodelist = parser.parse(('endmodule',))
    parser.delete_first_token()
    return ModuleNode(nodelist, title, width, color)

register.tag('module', do_module)