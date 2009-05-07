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

USER_KEY="vabqI2su93P1wVF3Ls9kXhXhRggV7y2ylokjq137yPAz47cY5dDMHgUA2QlZoWNE"
# The following is true for now
FORUM_KEY="9XGWB9o6NT1ZNiMtc2vt6ZJIUdp0D6sZDvis4hPfGGpsRaUchuH5c4fbO71GPAOj"

register = template.Library()

def tocloud(Tag):
	#return Tag.num_articles
	if Tag.num_articles > 2:
		html = 'largest'
	elif Tag.num_articles ==2:
		html = 'larger'
	elif Tag.num_articles == 1:
		html = 'medium'
	elif Tag.num_articles == 0:
		html = 'small'
	return mark_safe(html)

register.filter('tocloud', tocloud)