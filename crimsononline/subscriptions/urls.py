from django.conf.urls.defaults import *

# urls that start with /subscribe

urlpatterns = patterns('crimsononline.subscriptions.views',
    url(r'^email/$', 'signup'),
)