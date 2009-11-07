from django.conf.urls.defaults import *

# urls that start with /subscribe

urlpatterns = patterns('crimsononline.subscriptions.views',
    url(r'^$', 'index'),
    url(r'^email/$', 'email_signup'),
    url(r'^email/confirm/$', 'email_confirm'),
    url(r'^email/manage/$', 'email_manage'),
    url(r'^email/ajax/fb_find/(contributor|tag)/$', 'fbmc_search'),
)