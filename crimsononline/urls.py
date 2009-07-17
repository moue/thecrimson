from os import path
from django.conf import settings
from django.conf.urls.defaults import *
from django.contrib import admin
from django.conf.urls.defaults import *
from crimsononline.content.views import *
from crimsononline.admin_cust.views import login_user

admin.autodiscover()

FILTER_URL_RE = r'(?:sections/(?P<section_str>[A-Za-z,]+)/)?' \
    r'(?:types/(?P<type_str>[A-Za-z,\s]+)/)?' \
    r'(?:page/(?P<page>\d+)/)?' 
urlpatterns = patterns('crimsononline.content.views',
    url(r'writer/(?P<pk>\d+)/(?P<f_name>[A-Za-z\s]+)_' \
        r'(?P<m_name>[A-Za-z]?)_(?P<l_name>[A-Za-z\-\']+)/%s$' % FILTER_URL_RE,
        'writer', name='content_writer_profile'),
    url(r'^section/', include('crimsononline.content.section_urls')),
    url(r'^tag/(?P<tag>[A-Za-z\s]+)/%s$' % FILTER_URL_RE, 
        'tag', name='content_tag'),
    url(r'^gallery/(\d+)/(\d+)/$',
        'gallery', name='content_gallery'),
    url(r'^gallery/get_img/(\d+)/$', 'ajax_get_img'),
    #url(r'^search/', include('crimsononline.search.urls')),
    url(r'^search/', include('solango.urls')),
    url(r'^map/$', 'bigmap'),
    url(r'^$', 'index', name='content_index'),
    url(r'^issue/(\d+)/(\d+)/(\d+)/$', 'index', name='content_index'),    
    url(r'^subscribe/', include('crimsononline.subscriptions.urls')),
    url(r'^done$', 'subscribed'),
    url(r'^iphone/(?P<s>\w+)/$', 'iphone'),
)

urlpatterns += patterns('django.views.generic.simple',
    (r'login/$', 'redirect_to', { 'url': 'http://www.alondite.com/welp/crimlogin.html'}),
    (r'login_return/$', login_user),
)

urlpatterns += patterns('',
    (r'^admin/', include('crimsononline.admin_cust.urls')),
)

urlpatterns += patterns('',
    (r'^site_media/(?P<path>.*)$', 'django.views.static.serve', 
        {'document_root': settings.MEDIA_ROOT}),    
)

# generic content urls
CONTENT_URL_RE = r'([a-z\-]+)/(\d{4})/(\d{1,2})/(\d{1,2})/([0-9A-Za-z_\-]+)/$'
CGROUP_URL_RE = r'([a-z]+)/([a-z0-9\-]+)/'
generic_patterns = patterns('crimsononline.content.views',
    url('^' + CONTENT_URL_RE, 'get_content', name='content_content'),
    url('^' + CGROUP_URL_RE + CONTENT_URL_RE, 'get_grouped_content',
        name='content_grouped_content'),
    url('^' + CGROUP_URL_RE + '$', 'get_content_group', 
        name='content_contentgroup'),
)

urlpatterns += generic_patterns