from django.http import Http404, HttpResponse, HttpResponsePermanentRedirect
from django.conf.urls.defaults import *
from django.contrib import admin
from views import *

urlpatterns = patterns('',
    (r'^article\.aspx', redirect_article),
    (r'^writ er\.aspx', redirect_writer),
)

def redirect(url):
    def inner(request):
        return HttpResponsePermanentRedirect(url)
    return inner


urlpatterns += patterns('',
    ('^arts\.aspx', redirect('/section/arts/')),
    ('^news\.aspx', redirect('/section/news/')),
    ('^sports\.aspx', redirect('/section/sports/')),
    ('^opinion\.aspx', redirect('/section/opinion/')),
    ('^magazine\.aspx', redirect('/section/fm/')),
    ('^info/about\.aspx', redirect('/about/')),
    ('^info/privacy\.aspx', redirect('/about/privacy/')),
)
