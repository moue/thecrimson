from django.conf.urls.defaults import *

# urls that start with /subscribe

urlpatterns = patterns('crimsononline.subscriptions.views',
    url(r'^$', 'register'),
    url(r'^confirm/$', 'confirm'),
    url(r'^email/ajax/fb_find/(contributor|tag)/', 'fbmc_search'),
    url(r'^login/$','login'),
    url(r'^logout/$','logout'),
)