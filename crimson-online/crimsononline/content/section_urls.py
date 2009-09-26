from django.conf.urls.defaults import *
from django.views.generic.simple import redirect_to

urlpatterns = patterns('crimsononline.content.views',
    url(r'^photo/$', 'section_photo'),
    url(r'^news/$', 'section_news'),
    url(r'^opinion/$', 'section_opinion'),
    url(r'^fm/$', 'section_fm'),
    url(r'^fm/l/$', redirect_to, {'url': 'http://fmylife.com'}),
    url(r'^arts/$', 'section_arts'),
    url(r'^sports/$', 'section_sports'),
)