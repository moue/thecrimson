from django.conf.urls.defaults import *
from django.contrib import admin
from views import get_imgs

urlpatterns = patterns('',
    (r'^core/imagegallery/get_images/page/(\d+)', get_imgs),
)

urlpatterns += patterns('',
    (r'^(.*)', admin.site.root),
)