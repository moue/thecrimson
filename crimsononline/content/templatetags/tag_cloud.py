from django.db.models import Count
from django import template
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe
from content.models import Tag

register = template.Library()

@register.filter
def get_size(Tag, levels):
    if Tag.content_count > levels[0]:
        html = 'largest'
    elif Tag.content_count > levels[1]:
        html = 'larger'
    elif Tag.content_count > levels[2]:
        html = 'medium'
    else:
        html = 'small'
    return mark_safe(html)

class TagCloudNode(template.Node):
    """
    Generates a tag cloud.  
    2 requires arguments:
        The number of items in the cloud
        The title at the top
    
    If provided a list of tags, renders those.
    If not, grabs the tags with the highest amount of content.
    
    If you provide TagCloudNode with a list of tags, each item in the list
        must have the content_count attribute (to differentiate sizes by)
    
    TODO: restrict count to content in the past 3 months.
    """
    def __init__(self, num, title, tags):
        try:
            self.tags = template.Variable(tags)
        except:
            self.tags = None
        self.num = num if num else 20
        self.title = title
        
    def render(self, context):
        if self.tags:
            tags = self.tags
        else:
            tags = Tag.objects.all() \
                .annotate(content_count=Count('content')) \
                .order_by('-content_count')
            tags = list(tags[0:self.num])
        
        # base sizes on relative max, min of counts
        mx, mn = tags[0].content_count, tags[-1].content_count
        step = float(mx - mn) / 4.0
        levels = [mn + step * i for i in range(1, 4)]
        levels.reverse()
        
        # sort alphabetically
        tags.sort(lambda x,y: cmp(x.text, y.text))
        
        return render_to_string('templates/tagcloud.html', 
            {'tags': tags, 'levels': levels, 'title': self.title})

def do_tag_cloud(parser, token):
    tokens = token.split_contents()
    tags, num_tags = None, None
    if len(tokens) > 3:
        tags = tokens[3]
    if len(tokens) > 2:
        try:
            title = tokens[2]
            num_tags = int(tokens[1])
        except ValueError:
            raise template.TemplateSyntaxError, \
                "%r tag's first argument must be an integer" % tokens[0]
    else:
        raise template.TemplateSyntaxError, \
            "%r tag requires at least 2 arguments" % tokens[0]
    
    return TagCloudNode(num_tags, title[1:-1], tags)

register.tag('tag_cloud', do_tag_cloud)