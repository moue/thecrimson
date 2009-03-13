from django import template
from django.db import connection
from django.template import Context
from django.template.loader import get_template
from django.utils import simplejson
from django.utils.safestring import mark_safe
from crimsononline.content.models import Image, Article, Content, ContentGeneric
import urllib

USER_KEY="vabqI2su93P1wVF3Ls9kXhXhRggV7y2ylokjq137yPAz47cY5dDMHgUA2QlZoWNE"
# The following is true for now
FORUM_KEY="9XGWB9o6NT1ZNiMtc2vt6ZJIUdp0D6sZDvis4hPfGGpsRaUchuH5c4fbO71GPAOj"

register = template.Library()

@register.tag(name="most_read_articles")
def compile_most_read(parser, token):
    return TopArticlesNode()
    
class TopArticlesNode(template.Node):
    def render(self, context):
        # Step 1: We want to get the most viewed articles from the database
        cursor = connection.cursor()
        # SO GAY
        cursor.execute("SELECT DISTINCT content_article.id, " \
                       "(content_contentgeneric.hits * (1/(julianday('now') - julianday(content_article.created_on) + 2))) AS hitindex " \
                       "FROM content_article, content_contentgeneric WHERE content_contentgeneric.object_id = content_article.id ORDER BY hitindex DESC LIMIT 5")
        mostreadarticles = cursor.fetchall()
        mostreadarticles = map(lambda x: Article.objects.get(pk=x[0]), mostreadarticles)
        # Step 2: Grab the JSON crap from Disqus and build another list of the most commented articles
        url = "http://disqus.com/api/get_thread_list/?forum_api_key=" + FORUM_KEY
        thread_list = simplejson.load(urllib.urlopen(url))
        # access individual things by means of thread_list['message'][0], etc.
        
        t = get_template('mostreadarticles.html')
        html = t.render(Context({'mostreadarticleslist': mostreadarticles}))
        return html