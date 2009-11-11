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
	def inner(request):
		return redirect(Tag.objects.get(text=tag))
	return inner
	

urlpatterns += patterns('',
    (r'^index\.aspx', redirect('/')),
    (r'^arts\.aspx', redirect('/section/arts/')),
    (r'^news\.aspx', redirect('/section/news/')),
    (r'^sports\.aspx', redirect('/section/sports/')),
    (r'^opinion\.aspx', redirect('/section/opinion/')),
    (r'^magazine\.aspx', redirect('/section/fm/')),
)

urlpatterns += patterns('',
    (r'^archives\.aspx', redirect('/search/')),
	(r'^iraq\.aspx', redirect_tag('Iraq')),
	# TODO: commencement pages
	(r'^cambridge\.aspx', redirect_tag('Cambridge')),
	(r'^science\.aspx', redirect_tag('Science')),
	(r'^crime\.aspx', redirect_tag('Crime')),
	(r'^uc\.aspx', redirect_tag('Undergraduate Council')),
	(r'^news_page\.aspx', redirect('/section/news')),
	(r'^opinion_page\.aspx', redirect('/section/opinion')),
	(r'^sports_page\.aspx', redirect('/section/sports')),
	(r'^arts_page\.aspx', redirect('/section/arts')),
	(r'^photo_gallery\.aspx', redirect('/section/photo')),
	#(r'\w+\.aspx', redirect('/')), # Any aspx page we don't catch just goes to homepage. Potentially a terrible terrible terrible idea
)
	
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

urlpatterns += patterns('',
	#arts_features.aspx - unreachable
	(r'^artsblog\.aspx', redirect('/section/arts/')),
	#athleteoftheweek.aspx - page is broken
	#blogentry.aspx - page broken
	('^browse_by_issue\.aspx', redirect('/search/')),
	#calendar_menu.aspx - blank page
	(r'^cambridgenews\.aspx', redirect_tag('Cambridge')),
    (r'^classifieds\.aspx', redirect('/subscribe/')), # TODO
    #commencement pages should be done, should just paste in html from old site to flat page on new site
        #same with index_commencement2007.aspx
    #comics.aspx  - broken on this site
    #comment.aspx - just the comment box
    #confi.aspx - works on the site, decided would be too much work to recreate (also configuide2006)
    (r'^crisis\.aspx', redirect('/section/news')),
    (r'^dailygallery\.aspx', redirect('/section/photo')),
    (r'^donate\.aspx', redirect('/about/donate')),
    (r'^edigest\.aspx', redirect('/subscribe')),
    (r'^edigestmanage\.aspx', redirect('/subscribe')),
	(r'^editorialcartoons\.aspx', redirect('/section/opinion')),
    #election2008 should be done, should just paste in html from old site to flat page on new site
    #email is just the email story form
    #events can 404, no one should visit
    #fiction goes to a blank page
    (r'^gallery\.aspx', redirect('/section/photo')),
    (r'^gallery_new\.aspx', redirect('/section/photo')),
    #iraq.aspx should get the commencement page treatment (paste in html to flat page on new site)
    #journalismfair stuff can 404
    #layoffs.aspx is blank
    #login can 404
    #myfirstyear09.aspx is AWESOME and should definitely be transferred via the flat page method
    #neworleans.aspx can be put on a flat page
    #news_new is broken
    #news_page is broken
    #newstoday is also broken
    (r'^opinion_old\.aspx', redirect('/section/opinion')),
    #photorequest.aspx can 404
    #postblogcomment.aspx can 404
    #postcards08.aspx and postcards09.aspx should have their html transferred to a flat page
    #postcomment can 404
    #presidentialsearch.aspx is blank, can 404
    #printerfriendly.aspx can 404
    (r'^privacy\.aspx', redirect('/about/privacy/')),
    #propertymap.aspx should be pasted to a flat page
    #reportblogcomment.aspx can 404
    (r'^rss\.aspx', redirect('/subscribe')),
    (r'^science\.aspx', redirect_tag('Science')),
    #senddigest.aspx can 404
    (r'^terms\.aspx', redirect('/about/privacy/')),
    #uc.aspx should be pasted to new flat page
    #ucelection2007.aspx should link to the uc.aspx flat page
    #writer.aspx can 404 
    
    
)
""" TODO:

http://www.thecrimson.com/printerfriendly.aspx?ref=529893
Everything on the news page sidebar: http://www.thecrimson.com/news_page.aspx?teamid=2&beatid=15&page=1
Everything on info sidebar: http://www.thecrimson.com/info/ads.aspx

"""