from django import template
from django.core.exceptions import ObjectDoesNotExist
from crimsononline.content_module.models import ContentModule

register = template.Library()


class ContentModuleNode(template.Node):
    """
    Loads and renders a content module.  If the content module is empty,
    then everything between contentmodule and endcontentmodule is rendered.
    """
    def __init__(self, content_module, node_list):
        self.cm = content_module
        self.nodes = node_list
    
    def render(self, context):
        html = None
        try:
            self.cm = ContentModule.objects.get(name=self.cm)
            html = self.cm.html()
        except ObjectDoesNotExist:
            self.cm = ContentModule(name=self.cm)
            self.cm.save()
        except:
            pass
        return html or self.nodes.render(context)
    
@register.tag(name='contentmodule')
def do_content_module(parser, token):
    try:
        tag_name, content_module = token.split_contents()
    except ValueError:
        raise template.TemplateSyntaxError, \
            "%r tag requires a single argument" % token.contents.split()[0]
    if content_module[0] in ('"', "'") or content_module[-1] in ('"', "'"):
        raise template.TemplateSyntaxError, \
            "%r tag's argument should not be in quotes" % tag_name
    node_list = parser.parse(('endcontentmodule',))
    parser.delete_first_token()
    return ContentModuleNode(content_module, node_list)
    