from django.http import Http404, HttpResponse, HttpResponsePermanentRedirect
from django.views.decorators.cache import cache_page
from django.conf import settings

from crimsononline.content.models import *
from crimsononline.common.caching import funcache as cache

@cache(settings.CACHE_LONG, "general_content_article")
def redirect_article(request):
    try:
        id = request.GET.get("ref")
        a = Article.objects.get(pk=id)
        return HttpResponsePermanentRedirect(a.get_absolute_url())
    except:
        raise Http404

@cache(settings.CACHE_LONG, "general_content_writer")
def redirect_writer(request):
    try:
        id = request.GET.get("id")
        w = Contributor.objects.get(pk=id)
        return HttpResponsePermanentRedirect(w.get_absolute_url())
    except:
        raise Http404

@cache(settings.CACHE_LONG, "general_content_photo")
def redirect_photo(request,date,width,id):
    try:
        p = Image.objects.get(pk=id)
        spec = (width,0,0)
        return HttpResponsePermanentRedirect(p.display_url(spec))
    except:
        raise Http404
