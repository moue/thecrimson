from django.conf.urls.defaults import *
from django.views.generic.simple import redirect_to

urlpatterns = patterns('crimsononline.content.views',
    url(r'^news/$', 'iphone_news'),
    #url(r'^opinion/$', 'iphone_opinion'),
    #url(r'^fm/$', 'iphone_fm'),
    #url(r'^arts/$', 'iphone_arts'),
    #url(r'^sports/$', 'iphone_sports'),
)