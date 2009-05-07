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
from django.template.loader import get_template
from django.utils import simplejson
from django.utils.safestring import mark_safe
from crimsononline.content.models import Image, Article, Content, ContentGeneric
from crimsononline.urls import CONTENT_URL_RE, CGROUP_URL_RE
from content.models import *
from django.db.models import Count
import random
import array

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

class TagCloudNode(template.Node):
	def render(self, context):
		mostusedtags = Tag.objects.all().annotate(num_articles=Count('content')).order_by('-num_articles')
		mostusedtags_short = mostusedtags[0:25]		
		mostusedtags_short = list(mostusedtags_short)
		
		random.shuffle(mostusedtags_short)
		
		t = get_template('tagcloud.html')
		html = t.render(Context({'mostusedtags_short': mostusedtags_short}))
		return html

def do_tag_cloud(parser,token=5):
	return TagCloudNode()

@register.tag('tag_cloud',do_tag_cloud) 

def safe_resolve(url, resolver):
    try:
        return resolver.resolve(url)
    except Resolver404:
        return None
        