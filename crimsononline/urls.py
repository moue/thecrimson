from os import path
from django.conf import settings
from django.conf.urls.defaults import *
from django.contrib import admin
from crimsononline.content.views import *
from crimsononline.admin_cust.views import login_user

admin.autodiscover()

urlpatterns = patterns('crimsononline.content.views',
    #url(r'^article/(\d{4})/(\d{1,2})/(\d{1,2})/([-\w]+)/$',
    #    'article', name='content_get_article'),
    url(r'^writer/(\d+)/([A-Za-z\s]+)_([A-Za-z]{0,1})_([A-Za-z]+)/$',
        'writer', name='content_writer_profile'),
    url(r'^section/(?P<section>[A-Za-z]+)/$', 'section', name='content_section'),
    url(r'^section/(?P<section>[A-Za-z]+)/issue/(?P<issue_id>\d+)$',
        'section', name='content_section_by_issue'),
    url(r'^section/(?P<section>[A-Za-z]+)/tag/(?P<tags>[A-Za-z\s,]+)/$', 
        'section', name='content_section_by_tag'),
    url(r'^tag[s]{0,1}/(?P<tags>[A-Za-z\s,]+)/$', 'tag', name='content_tag'),
    #url(r'^image/(\d{4})/(\d{1,2})/(\d{1,2})/([-\w]+)/$',
    #    'image', name='content_get_image'),
    url(r'^gallery/(\d+)/(\d+)/$',
        'gallery', name='content_imagegallery'),
    url(r'^gallery/get_img/(\d+)/$', 'ajax_get_img'),
    url(r'^search/', include('crimsononline.search.urls')),
    url(r'^map/$', 'bigmap'),
    url(r'^$', 'index', name='content_index'),
)

urlpatterns += patterns('django.views.generic.simple',
    (r'login/$', 'redirect_to', { 'url': 'http://www.alondite.com/welp/crimlogin.html'}),
    (r'login_return/$', login_user),
)

urlpatterns += patterns('',
    (r'^admin/', include('crimsononline.admin_cust.urls')),
)

urlpatterns += patterns('',
    (r'^site_media/(?P<path>.*)$', 
        'django.views.static.serve', 
        {'document_root': settings.MEDIA_ROOT}),
)

# generic content urls
CONTENT_URL_RE = r'([a-z]+)/(\d{4})/(\d{1,2})/(\d{1,2})/([0-9A-Za-z_.]+)/(\d+)$'
CGROUP_URL_RE = r'([a-z]+)/([A-Za-z0-9_]+)/'
urlpatterns += patterns('crimsononline.content.views',
    url('^' + CONTENT_URL_RE, 'get_content', name='content_content'),
    url('^' + CGROUP_URL_RE + CONTENT_URL_RE + '$', 'get_grouped_content',
        name='content_grouped_content'),
    url('^' + CGROUP_URL_RE + '$', 'get_content_group', 
        name='content_contentgroup'),
)