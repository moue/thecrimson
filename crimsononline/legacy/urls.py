from django.http import Http404, HttpResponse, HttpResponsePermanentRedirect
from django.conf.urls.defaults import *
from django.contrib import admin
from views import *

urlpatterns = patterns('',
    (r'^article\.aspx', redirect_article),
    (r'^writer\.aspx', redirect_writer),
    ('^(?P<date>\d+-\d+-\d+)/pic-(?P<width>\d+)-(?P<id>\d+)\.jpg', redirect_photo), # links go to http://media.thecrimson.com/_____ so make sure we catch this
)

def redirect(url):
    def inner(request):
        return HttpResponsePermanentRedirect(url)
    return inner


urlpatterns += patterns('',
    ('^index\.aspx', redirect('/')),
    
    ('^arts\.aspx', redirect('/section/arts/')),
    ('^news\.aspx', redirect('/section/news/')),
    ('^sports\.aspx', redirect('/section/sports/')),
    ('^opinion\.aspx', redirect('/section/opinion/')),
    ('^magazine\.aspx', redirect('/section/fm/')),
)

urlpatterns += patterns('',
    ('^info/archives\.aspx', redirect('/search/')),
    ('^info/ads\.aspx', redirect('/about/advertising/')),
    ('^info/classifieds\.aspx', redirect('/subscribe/')), # TODO
    ('^info/corrections\.aspx', redirect('/about/corrections/')),
    ('^info/contacts\.aspx', redirect('/about/contact/')),
    ('^info/deliveries\.aspx', redirect('/subscribe/')), #TODO
    ('^info/privacy\.aspx', redirect('/about/privacy/')),
    ('^info/rss\.aspx', redirect('/subscribe/')),
    ('^info/subscriptions\.aspx', redirect('/subscribe/')),
    ('^info/terms\.aspx', redirect('/about/permissions/')),
)

""" TODO:

http://www.thecrimson.com/printerfriendly.aspx?ref=529893
Everything on the news page sidebar: http://www.thecrimson.com/news_page.aspx?teamid=2&beatid=15&page=1
Everything on info sidebar: http://www.thecrimson.com/info/ads.aspx

"""