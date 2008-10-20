from django.conf.urls.defaults import *
from django.contrib import admin
from views import get_imgs, get_img_gallery, get_img_galleries, find_contributors

urlpatterns = patterns('',
    (r'^core/imagegallery/get_images/pk/(?P<pk>\d+)/$', get_imgs),
    (r'^core/imagegallery/get_images/page/(?P<page>\d+)/$', get_imgs),
    (r'^core/imagegallery/get_img_gallery/(\d{4})/(\d{1,2})/(\d{4})/(\d{1,2})/([\w\-,]+)/(\d+)/$', get_img_galleries),
    (r'^core/imagegallery/get_img_gallery/(img|gal)/(\d+)/$', get_img_gallery),
    (r'^core/contributor/search/$', find_contributors),
)

urlpatterns += patterns('',
    (r'^(.*)', admin.site.root),
)