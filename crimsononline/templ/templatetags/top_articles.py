from django import template
from django.db import connection
from django.template import Context
from django.template.loader import get_template
from django.utils import simplejson
from django.utils.safestring import mark_safe
from crimsononline.content.models import Image, Article, Content, ContentGeneric
from datetime import datetime, timedelta
from math import log
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
        """
        # Step 2: Grab the JSON crap from Disqus and build another list of the most commented articles
        thread_url = "http://disqus.com/api/get_thread_list/?forum_api_key=" + FORUM_KEY
        thread_list = simplejson.load(urllib.urlopen(thread_url))
        # for each thread, grab its posts, then compute the popularity of the thread based on their recency
        for thread in thread_list['message']:
            thread_posts_url = "http://disqus.com/api/get_thread_posts/?forum_api_key=" + FORUM_KEY + "&thread_id=" & thread['id']
            thread_posts = simplejson.load(urllib.urlopen(thread_posts_url))
            thread['comment_index'] = 0
            for post in thread_posts['message']:
                tdelta = datetime.now() - datetime.strptime(post['created_at'], "%Y-%m-%dT%H:%M")
                thread['comment_index'] += 1 / log((tdelta.days + tdelta.seconds / 86400) + 2)
        # sort the thread list
        thread_list['message'].sort(lambda x, y: cmp(int(x['comment_index'], y['comment_index'])))
        # Finish this later (need to get articles based on their URL; we can probably grab the ID out of the URL string in the dict
        # mostcommentedarticleslist = map(lambda x: Article.objects.get(
        """
        t = get_template('mostreadarticles.html')
        html = t.render(Context({'mostreadarticleslist': mostreadarticles}))
        return html