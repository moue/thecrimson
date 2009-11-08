from django import template
from django.template.loader import render_to_string
from crimsononline.content.models import Content, ContentGroup, Article

register = template.Library()

class FlyByNode(template.Node):
    """
    Generates a flyby widget.
    """

    def __init__(self):
        pass
    
    def render(self, context):
        fbb = ContentGroup.objects.get(name="FlyBy")
        self.posts = Article.objects.filter(group__id=fbb.id)[:3]
        filenames = ['images/flyby/flybyicon0.png', 'images/flyby/flybyicon1.png', 'images/flyby/flybyicon2.png', 'images/flyby/flybyicon3.png']
        return render_to_string('templatetag/flyby_preview.html', 
            {'posts': self.posts, 'filenames': filenames,})
    

def do_flyby(parser, token, nopreview=False):
    return FlyByNode()


register.tag('flyby_preview', do_flyby)
