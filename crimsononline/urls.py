from os import path
from django.conf import settings
from django.conf.urls.defaults import *
from django.contrib import admin
from crimsononline.core.views import *

admin.autodiscover()

urlpatterns = patterns('crimsononline.core.views',
    url(r'^article/(\d+)', 'article', name='core_get_single_article'),
    url(r'^writer/(\d+)', 'writer', name='core_writer_profile'),
    url(r'^section/(?P<section>[A-Za-z]+)/$', 'section', name='core_section'),
    url(r'^section/(?P<section>[A-Za-z]+)/issue/(?P<issue_id>\d+)$', 'section', 
        name='core_section_by_issue'),
    #url(r'^tag/(?P<tag_name>[A-Za-z0-9+]+)/$', 'tag', name='core_tag'),
    url(r'^tag[s]{0,1}/(?P<tags>[A-Za-z\s,]+)/$', 'tag', name='core_tag'),
    url(r'^$', 'index', name='core_index'),
)

urlpatterns += patterns('',
    (r'^admin/', include('admin_cust.urls')),
)

urlpatterns += patterns('',
    (r'^site_media/(?P<path>.*)$', 
        'django.views.static.serve', 
        {'document_root': settings.MEDIA_ROOT}),
)