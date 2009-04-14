from datetime import datetime, timedelta
from math import log
import urllib
from urlparse import urlparse
from django import template
from django.conf.urls.defaults import patterns, url
from django.core.urlresolvers import RegexURLResolver, Resolver404
from django.db import connection
from django.template import Context
from django.template.loader import get_template
from django.utils import simplejson
from django.utils.safestring import mark_safe
from crimsononline.content.models import Image, Article, Content, ContentGeneric
from crimsononline.urls import CONTENT_URL_RE, CGROUP_URL_RE

USER_KEY="vabqI2su93P1wVF3Ls9kXhXhRggV7y2ylokjq137yPAz47cY5dDMHgUA2QlZoWNE"
# The following is true for now
FORUM_KEY="9XGWB9o6NT1ZNiMtc2vt6ZJIUdp0D6sZDvis4hPfGGpsRaUchuH5c4fbO71GPAOj"

generic_obj_patterns = patterns('crimsononline.content.views',
    url('^' + CONTENT_URL_RE, 'get_content_obj', name='content_content'),
    url('^' + CGROUP_URL_RE + CONTENT_URL_RE + '$', 'get_grouped_content_obj',
        name='content_grouped_content'),
    url('^' + CGROUP_URL_RE + '$', 'get_content_group_obj', 
        name='content_contentgroup'),
)

register = template.Library()

@register.tag(name="most_read_articles")
def compile_most_read(parser, token):
    return TopArticlesNode()
    
def safe_resolve(url, resolver):
    try:
        return resolver.resolve(url)
    except Resolver404:
        return None
        
def call_view(view, args):
    try:
        return view(*([None] + list(args)))
    except ContentGeneric.DoesNotExist:
        return None
    
class TopArticlesNode(template.Node):
    def render(self, context):
        # Step 1: We want to get the most viewed articles from the database
        cursor = connection.cursor()
        # SO NON-SEXUALITY-NORMATIVE
        cursor.execute("SELECT DISTINCT content_article.id, " \
                       "(content_contentgeneric.hits * (1/(julianday('now') - julianday(content_article.created_on) + 2))) AS hitindex " \
                       "FROM content_article, content_contentgeneric WHERE content_contentgeneric.object_id = content_article.id ORDER BY hitindex DESC LIMIT 5")
        mostreadarticles = cursor.fetchall()
        mostreadarticles = map(lambda x: Article.objects.get(pk=x[0]), mostreadarticles)
        
        # Step 2: Grab the JSON crap from Disqus and build another list of the most commented articles
        thread_url = "http://disqus.com/api/get_thread_list/?forum_api_key=" + FORUM_KEY
        thread_list = simplejson.load(urllib.urlopen(thread_url))
        # for each thread, grab its posts, then compute the popularity of the thread based on their recency
        for thread in thread_list['message']:
            thread_posts_url = "http://disqus.com/api/get_thread_posts/?forum_api_key=" + FORUM_KEY + "&thread_id=" + thread['id']
            thread_posts = simplejson.load(urllib.urlopen(thread_posts_url))
            thread['comment_index'] = 0
            for post in thread_posts['message']:
                tdelta = datetime.now() - datetime.strptime(post['created_at'], "%Y-%m-%dT%H:%M")
                thread['comment_index'] += 1 / log((tdelta.days + tdelta.seconds / 86400) + 2)
        # sort the thread list
        # thread_list['message'].sort(lambda x, y: cmp(float(x['comment_index']), float(y['comment_index'])))
        thread_list['message'].sort(lambda x, y: cmp(float(y['comment_index']), float(x['comment_index'])))
        # Finish this later (need to get articles based on their URL; we can probably grab the ID out of the URL string in the dict
        # mostcommentedarticleslist = map(lambda x: Article.objects.get(
        resolver = RegexURLResolver(r'^/', generic_obj_patterns)
        # call resolver.resolve on everything in the list
        urllist = map(lambda x: (urlparse(x['url']))[2], thread_list['message'])
        threadobjlist = map(lambda x: safe_resolve(x, resolver), urllist)
        mostcommentedarticles = map(lambda x: call_view(x[0], x[1]), filter(lambda x: x != None, threadobjlist))
        del mostcommentedarticles[5:]
        
        """
         THE PLAN HERE:
         Copy and paste the generic urlpatterns from urls.py.  Create an instance of RegexURLResolver and have it resolve the
         URL with that pattern, giving us the view function that will give us the article object or nothing at all.
         Once we have that info, we can call the view on the parameters (it's not a real view since it doesn't return an
         HTTPResponse) and get the object for the article, which can then be put into the mostcommentedarticles list.
         """
        
        t = get_template('mostreadarticles.html')
        html = t.render(Context({'mostreadarticles': mostreadarticles, 'mostcommentedarticles': mostcommentedarticles}))
        return html