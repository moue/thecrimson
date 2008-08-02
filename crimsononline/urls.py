from django.conf.urls.defaults import *
from django.contrib import admin
from crimsononline.core.views import *

admin.autodiscover()

urlpatterns = patterns('crimsononline.core.views',
    url(r'^article/(\d+)', 'article', name='core_get_single_article'),
    url(r'^writer/(\d+)', 'writer', name='core_writer_profile'),
    url(r'^news/(\d+)', 'daily_news', name='core_daily_news'),
    url(r'^news/$', 'daily_news', name='core_daily_news_default'),
    url(r'^$', 'index', name='core_index'),
)

urlpatterns += patterns('',
    (r'^admin/(.*)', admin.site.root),
)

urlpatterns += patterns('',
    (r'^site_media/(?P<path>.*)$', 
        'django.views.static.serve', 
        {'document_root': '/Users/andylei/Sites/django/crimson-online/crimsononline/static'}),
)
