from django import template
from django.template.loader import render_to_string
from crimsononline.content.models import Content, Section, Article

register = template.Library()

class FlyByNode(template.Node):
    """
    Generates a flyby widget.
    """
    def render(self, context):
        fbb = Section.cached('flyby')
        self.posts = Article.objects.recent.filter(section=fbb)[:3]
        filenames = ['flybyicon0', 'flybyicon1', 'flybyicon2', 'flybyicon3']
        filenames = ['images/flyby/%s.png' % s for s in filenames]
        return render_to_string('templatetag/flyby_preview.html', 
            {'posts': self.posts, 'filenames': filenames,})
    

def do_flyby(parser, token, nopreview=False):
    return FlyByNode()

register.tag('flyby_preview', do_flyby)
