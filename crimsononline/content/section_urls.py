from django.conf.urls.defaults import *
from django.http import Http404, HttpResponse, HttpResponsePermanentRedirect
from django.views.generic.simple import redirect_to
from crimsononline.urls import CGROUP_FILTER_URL_RE

def redirect(url):
    def inner(request):
        return HttpResponsePermanentRedirect(url)
    return inner

urlpatterns = patterns('crimsononline.content.views',
    url(r'^news/$', 'section_news', name='content.section.news'),
    url(r'^sports/$', 'section_sports', name='content.section.sports'),
    url(r'^media/$', 'section_media', name='content.section.media'),
    url(r'^opinion/$', 'section_opinion', name='content.section.opinion'),
    url(r'^flyby/' + CGROUP_FILTER_URL_RE + '$', 'section_flyby', name='content.section.flyby'),
    url(r'^flyby/tip/$', 'flyby_tip', name='content.section.flyby_tip'),
    url(r'^fm/$', 'section_fm', name='content.section.fm'),
    url(r'^fml/$', redirect_to, {'url': 'http://fmylife.com'}),
    url(r'^arts/$', 'section_arts', name='content.section.arts'),
    url(r'^photo/$', redirect('/section/media/')),
)
