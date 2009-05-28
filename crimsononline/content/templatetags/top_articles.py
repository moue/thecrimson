from datetime import datetime, timedelta
from math import log
import time
import urllib
from urlparse import urlparse
from django import template
from django.conf.urls.defaults import patterns, url
from django.contrib.contenttypes.models import ContentType
from django.core.urlresolvers import RegexURLResolver, Resolver404
from django.db import connection
from django.template import Context
from django.template.loader import get_template, render_to_string
from django.utils import simplejson
from django.utils.safestring import mark_safe
from operator import itemgetter
try:
    from googleanalytics import Connection
except:
    Connection = None
from crimsononline.content.models import Image, Article, Content, ContentGeneric
from crimsononline.urls import CONTENT_URL_RE, CGROUP_URL_RE

D_USER_KEY = "vabqI2su93P1wVF3Ls9kXhXhRggV7y2ylokjq137yPAz47cY5dDMHgUA2QlZoWNE"
# The following is true for now
D_FORUM_KEY = "9XGWB9o6NT1ZNiMtc2vt6ZJIUdp0D6sZDvis4hPfGGpsRaUchuH5c4fbO71GPAOj"

GA_LOGIN = "crimsonanalytics@gmail.com"
GA_PASS = "andylei:male"
GA_AID = "509545"

# Below falues roughly based on values of 1/log(days + 1.5)
# Last day
TP1_FACTOR = 3.6
# Last week
TP2_FACTOR = 1.35
# Last month
TP3_FACTOR = 0.76
TP1_TIMEDELTA = timedelta(days = 1)
TP2_TIMEDELTA = timedelta(days = 7)
TP3_TIMEDELTA = timedelta(days = 30)

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
        # Create a resolver for the slightly modified URL patterns we defined above
        resolver = RegexURLResolver(r'^/', generic_obj_patterns)
        # Step 1: We want to get the most viewed articles from the database
        cursor = connection.cursor()
        # SO NON-SEXUALITY-NORMATIVE
        # Oh, a real comment in case someone comes upon this later: We're selecting article ID, content type ID, and a computed field called "hitindex"
        # which will eventually use log() for a better curve.  This ages articles' hits to reduce freshness.  Then it sorts by hitindex and returns the top 5.
        # TODO: Fix this to use proper decay when we switch to a real SQL server
        cursor.execute("SELECT DISTINCT content_article.id, content_contentgeneric.content_type_id, SUM(content_contenthits.hits) AS hitnum FROM content_article, " \
                       "content_contentgeneric, content_contenthits WHERE content_contentgeneric.object_id = content_article.id AND content_contenthits.content_generic_id " \
                       "= content_contentgeneric.id AND content_contenthits.date > date('now', '-7 days') GROUP BY content_contenthits.content_generic_id ORDER BY hitnum DESC LIMIT 5")
        mostreadarticles = cursor.fetchall()
        mostreadarticles = [(ContentType.objects.get(pk=x[1])).get_object_for_this_type(pk=x[0]) for x in mostreadarticles]
        
        # Step 2: Grab the JSON crap from Disqus and build another list of the most commented articles
        thread_url = "http://disqus.com/api/get_thread_list/?forum_api_key=" + D_FORUM_KEY
        thread_list = simplejson.load(urllib.urlopen(thread_url))
        # for each thread, grab its posts, then compute the popularity of the thread based on their recency
        for thread in thread_list['message']:
            thread_posts_url = "http://disqus.com/api/get_thread_posts/?forum_api_key=" + D_FORUM_KEY + "&thread_id=" + thread['id']
            thread_posts = simplejson.load(urllib.urlopen(thread_posts_url))
            thread['comment_index'] = 0
            for post in thread_posts['message']:
                # I think Guido is a pretty cool guy, he kills breins and doesn't afraid of any ridiculous hack to implement functionality present in every language not maintained by retards
                tdelta = datetime.now() - (datetime.strptime(post['created_at'], "%Y-%m-%dT%H:%M") - timedelta(0, time.timezone, 0, 0, 0, -time.daylight, 0))
                thread['comment_index'] += 1 / log((tdelta.days + float(tdelta.seconds) / 86400) + 2)
        # sort the thread list
        thread_list['message'].sort(lambda x, y: cmp(float(y['comment_index']), float(x['comment_index'])))
        
        
        # call resolver.resolve on everything in the list
        urllist = map(lambda x: (urlparse(x['url']))[2], thread_list['message'])
        threadobjlist = map(lambda x: safe_resolve(x, resolver), urllist)
        mostcommentedarticles = map(lambda x: call_view(x[0], x[1]), filter(lambda x: x != None, threadobjlist))
        # Only want top 5 -- we need to do this last because we're not guaranteed that there won't be some gaps in threadobjlist
        del mostcommentedarticles[5:]
        
        """
         THE PLAN HERE:
         Copy and paste the generic urlpatterns from urls.py.  Create an instance of RegexURLResolver and have it resolve the
         URL with that pattern, giving us the view function that will give us the article object or nothing at all.
         Once we have that info, we can call the view on the parameters (it's not a real view since it doesn't return an
         HTTPResponse) and get the object for the article, which can then be put into the mostcommentedarticles list.
         """
        
        return render_to_string('templatetag/mostreadarticles.html',
            {'mostreadarticles': mostreadarticles, 
                'mostcommentedarticles': mostcommentedarticles})