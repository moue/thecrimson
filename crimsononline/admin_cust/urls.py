from django.conf.urls.defaults import *
from django.contrib import admin
from views import *

urlpatterns = patterns('',
    (r'^core/imagegallery/get_images/pk/(?P<pk>\d+)/$', get_imgs),
    (r'^core/imagegallery/get_images/page/(?P<page>\d+)/$', get_imgs),
    (r'^core/imagegallery/get_img_gallery/(\d{4})/(\d{1,2})/(\d{4})/(\d{1,2})/([\w\-,]+)/(\d+)/$', get_img_galleries),
    (r'^core/imagegallery/get_img_gallery/(img|gal)/(\d+)/$', get_img_gallery),
    (r'^core/contributor/search/$', get_contributors),
    (r'^core/issue/issue_list/$', get_issues),
    (r'^core/issue/special_issue_list/$', get_special_issues),
    (r'^core/rel_content/find/(\d+)/(\d\d/\d\d/\d{4})/(\d\d/\d\d/\d{4})/([\w\-,]*)/(\d+)/$', find_rel_content),
    (r'^core/rel_content/get/(\d+)/(\d+)/$', get_rel_content),
    (r'^core/rel_content/get/(?P<ct_name>\w+)/(?P<obj_id>\d+)/$',
        get_rel_content, {'ct_id': 0})
)

urlpatterns += patterns('',
    (r'^doc/', include('django.contrib.admindocs.urls')),
    (r'^(.*)', admin.site.root),
)