from django.conf.urls.defaults import *

urlpatterns = patterns('crimsononline.admin.views',
	#(r'^core/article/add/$', 'edit_article'),
	#(r'^core/article/(?P<article_id>\d+)/$', 'edit_article'),
	#(r'^core/article/get_contributor', 'get_contributor')
)

urlpatterns += patterns('',
	(r'^', include('django.contrib.admin.urls')),
)