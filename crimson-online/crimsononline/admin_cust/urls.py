from django.conf.urls.defaults import *
from django.contrib import admin
from views import *

urlpatterns = patterns('',
    (r'^content/gallery/get_images/pk/(?P<pk>\d+)/$', get_imgs),
    (r'^content/gallery/get_images/page/(?P<page>\d+)/$', get_imgs),
    (r'^content/gallery/get_gallery/(\d{4})/(\d{1,2})/(\d{4})/(\d{1,2})/([\w\-,]+)/(\d+)/$', get_galleries),
    (r'^content/gallery/get_gallery/(img|gal)/(\d+)/$', get_gallery),
)

urlpatterns += patterns('',
    (r'^doc/', include('django.contrib.admindocs.urls')),
    (r'^', include(admin.site.urls)),
)