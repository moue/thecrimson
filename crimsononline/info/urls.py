from django.conf.urls.defaults import *

# urls that start with /about

urlpatterns = patterns('crimsononline.info.views',
    url(r'^contact/', 'contact'),
    url(r'^corrections/', 'contact'),
    url(r'^thanks/', 'thank'),
)