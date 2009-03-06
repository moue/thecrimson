from django import template
from django.db import connection
from django.template import Context
from django.template.loader import get_template
from django.utils.safestring import mark_safe
from crimsononline.core.models import Image, Article, Content, ContentGeneric

register = template.Library()

@register.tag(name="most_read_articles")
def compile_most_read(parser, token):
    return TopArticlesNode()
    
class TopArticlesNode(template.Node):
    def render(self, context):
        cursor = connection.cursor()
        # SO GAY
        cursor.execute("SELECT id, " \
                       "(10 * (1/(julianday('now') - julianday(core_article.created_on) + 2))) AS hitindex " \
                       "FROM core_article ORDER BY hitindex DESC LIMIT 5")
        toparticles = cursor.fetchall()
        toparticles = map(lambda x: Article.objects.get(pk=x[0]), toparticles)
        t = get_template('mostreadarticles.html')
        html = t.render(Context({'articlelist': toparticles}))
        return html