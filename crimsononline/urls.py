from os import path
from django.conf import settings
from django.conf.urls.defaults import *
from django.contrib import admin
from crimsononline.core.views import *

admin.autodiscover()

urlpatterns = patterns('crimsononline.core.views',
    url(r'^article/(\d{4})/(\d{1,2})/(\d{1,2})/([-\w]+)/$',
        'article', name='core_get_article'),
    url(r'^writer/(\d+)/([A-Za-z]+)_([A-Za-z]{0,1})_([A-Za-z]+)/$',
        'writer', name='core_writer_profile'),
    url(r'^section/(?P<section>[A-Za-z]+)/$', 'section', name='core_section'),
    url(r'^section/(?P<section>[A-Za-z]+)/issue/(?P<issue_id>\d+)$',
        'section', name='core_section_by_issue'),
    url(r'^section/(?P<section>[A-Za-z]+)/tag/(?P<tags>[A-Za-z\s,]+)/$', 
        'section', name='core_section_by_tag'),
    url(r'^tag[s]{0,1}/(?P<tags>[A-Za-z\s,]+)/$', 'tag', name='core_tag'),
    url(r'^gallery/(\d+)/(\d+)/$',
        'gallery', name='core_imagegallery'),
    url(r'^gallery/get_img/(\d+)/$', 'ajax_get_img'),
    url(r'^$', 'index', name='core_index'),
)

urlpatterns += patterns('',
    (r'^admin/', include('crimsononline.admin_cust.urls')),
)

urlpatterns += patterns('',
    (r'^site_media/(?P<path>.*)$', 
        'django.views.static.serve', 
        {'document_root': settings.MEDIA_ROOT}),
)