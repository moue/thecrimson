from django.http import Http404, HttpResponse, HttpResponsePermanentRedirect
from django.conf.urls.defaults import *
from django.contrib import admin
from views import *

urlpatterns = patterns('',
    (r'^article\.aspx', redirect_article),
    (r'^writer\.aspx', redirect_writer),
    (r'^(?P<date>\d+-\d+-\d+)/pic-(?P<width>\d+)-(?P<id>\d+)\.jpg', redirect_photo), # links go to http://media.thecrimson.com/_____ so make sure we catch this
)

def redirect(url):
    def inner(request):
        return HttpResponsePermanentRedirect(url)
    return inner

def redirect_tag(tag):
	return redirect(Tag.objects.get(text=tag))
	

urlpatterns += patterns('',
    (r'^index\.aspx', redirect('/')),
    
    (r'^arts\.aspx', redirect('/section/arts/')),
    (r'^news\.aspx', redirect('/section/news/')),
    (r'^sports\.aspx', redirect('/section/sports/')),
    (r'^opinion\.aspx', redirect('/section/opinion/')),
    (r'^magazine\.aspx', redirect('/section/fm/')),
)

urlpatters += patterns('',
	(r'iraq\.aspx', redirect_tag('Iraq')),
	# TODO: commencement pages
	(r'cambridge\.aspx', redirect_tag('Cambridge')),
	(r'science\.aspx', redirect_tag('Science')),
	(r'crime\.aspx', redirect_tag('Crime')),
	(r'uc\.aspx', redirect_tag('Undergraduate Council')),
	(r'^news_page\.aspx', redirect('/section/news')),
	(r'^opinion_page\.aspx', redirect('/section/opinion')),
	(r'^sports_page\.aspx', redirect('/section/sports')),
	(r'^arts_page\.aspx', redirect('/section/arts')),
	(r'^photo_gallery\.aspx', redirect('/section/photo')),
	#(r'\w+\.aspx', redirect('/')), # Any aspx page we don't catch just goes to homepage. Potentially a terrible terrible terrible idea

urlpatterns += patterns('',
    (r'^info/archives\.aspx', redirect('/search/')),
    (r'^info/ads\.aspx', redirect('/about/advertising/')),
    (r'^info/classifieds\.aspx', redirect('/subscribe/')), # TODO
    (r'^info/corrections\.aspx', redirect('/about/corrections/')),
    (r'^info/contacts\.aspx', redirect('/about/contact/')),
    (r'^info/deliveries\.aspx', redirect('/subscribe/')), #TODO
    (r'^info/privacy\.aspx', redirect('/about/privacy/')),
    (r'^info/rss\.aspx', redirect('/subscribe/')),
    (r'^info/subscriptions\.aspx', redirect('/subscribe/')),
    (r'^info/terms\.aspx', redirect('/about/permissions/')),
)

""" TODO:

http://www.thecrimson.com/printerfriendly.aspx?ref=529893
Everything on the news page sidebar: http://www.thecrimson.com/news_page.aspx?teamid=2&beatid=15&page=1
Everything on info sidebar: http://www.thecrimson.com/info/ads.aspx

"""