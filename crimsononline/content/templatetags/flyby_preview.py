from django import template
from django.template.loader import render_to_string
from crimsononline.content.models import Content, Section, Article, ContentGroup

register = template.Library()

class FlyByNode(template.Node):
    """
    Generates a flyby widget.
    """
    def render(self, context):
        fbb = Section.cached('flyby')
        self.posts = Article.objects.recent.filter(section=fbb)[:4]
        filenames = ['flybyicon0', 'flybyicon1', 'flybyicon2', 'flybyicon3']
        filenames = ['images/flyby/%s.png' % s for s in filenames]
        return render_to_string('templatetag/flyby_preview.html', 
            {'posts': self.posts, 'filenames': filenames,})
    

def do_flyby(parser, token, nopreview=False):
    return FlyByNode()

register.tag('flyby_preview', do_flyby)

class BlogNode(template.Node):
    """
    Generates a blog widget thing that doesn't have the Flyby logo.
    TODO: Generalize this so that it works for contentgroups that are not the sports blog.
    """
    def render(self, context):
        sb = ContentGroup.objects.get(name='The Back Page')
        self.posts = Article.objects.recent.filter(group=sb)[:4]
        return render_to_string('templatetag/blog_preview.html', 
            {'posts': self.posts,})
    

def do_blog(parser, token, nopreview=False):
    return BlogNode()

register.tag('blog_preview', do_blog)