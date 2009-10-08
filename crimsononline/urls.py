from os import path
from django.conf import settings
from django.conf.urls.defaults import *
from django.contrib import admin
from django.conf.urls.defaults import *
from crimsononline.content.views import *
from crimsononline.admin_cust.views import login_user
from django.contrib.auth.views import login, logout
from django.contrib.sitemaps import FlatPageSitemap
from crimsononline.content.sitemaps import ArticleSitemap

admin.autodiscover()

FILTER_URL_RE = r'(?:sections/(?P<section_str>[A-Za-z,]+)/)?' \
    r'(?:types/(?P<type_str>[A-Za-z,\s]+)/)?' \
    r'(?:page/(?P<page>\d+)/)?'

from crimsononline.content import feeds

urlpatterns = patterns('',
)

urlpatterns += patterns('crimsononline.content.views',
    url(r'writer/(?P<pk>\d+)/(?P<f_name>[A-Za-z\-\'\.\s]+)_' \
        r'(?P<m_name>[A-Za-z\-\'\.\s]*)_(?P<l_name>[A-Za-z\-\'\.\s]+)/%s$' % FILTER_URL_RE,
        'writer', name='content_writer_profile'),
    url(r'^section/', include('crimsononline.content.section_urls'), name='content_section'),
    url(r'^tag/(?P<tag>[A-Za-z\'\s]+)/%s$' % FILTER_URL_RE, 
        'tag', name='content_tag'),
    url(r'^$', 'index', name='content_index'),
    url(r'^issue/(\d+)/(\d+)/(\d+)/$', 'index', name='content_index'),    
    url(r'^subscribe/', include('crimsononline.subscriptions.urls')),
    url(r'^iphone/(?P<s>\w+)/$', 'iphone'),
)

feeds = {
    'latest': feeds.Latest,
    'section': feeds.BySection,
    'author': feeds.ByAuthor,
    'tag': feeds.ByTag,
}


sitemaps = {
    'flatpages': FlatPageSitemap,
    'articles': ArticleSitemap,
}

urlpatterns +=patterns('',
    url(r'^feeds/(?P<url>.*)/$', 'django.contrib.syndication.views.feed', {'feed_dict': feeds}),
    url(r'^sitemap.xml$', 'django.contrib.sitemaps.views.index', {'sitemaps': sitemaps}),
    url(r'^sitemap-(?P<section>.+)\.xml$', 'django.contrib.sitemaps.views.sitemap', {'sitemaps': sitemaps}),
)

if settings.HAYSTACK:
    urlpatterns += patterns('',
        url(r'^search/', include('haystack.urls')),
    )

"""
urlpatterns += patterns('django.views.generic.simple',
    (r'login/$', 'redirect_to', { 'url': 'http://www.alondite.com/welp/crimlogin.html'}),
    (r'login_return/$', login_user),
)
"""



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

# old website urls intact
urlpatterns += patterns('crimsononline.content.views',
    (r'^article\.aspx', 'get_article_old_website')
)

urlpatterns += generic_patterns