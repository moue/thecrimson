from django.core.cache import cache
from django.http import HttpResponse, HttpResponseRedirect
from django.db import models
from crimsononline.content.models import Content
from django.conf import settings

#Checks the cache to see if we have entered SUPER CRISIS MODE
#If so, it redirects all other requests to the home page, and 
#for homepage requests it renders a single article that is
#defined in the admin interface
class SuperCrisisMode(object):
    def process_request(self, request):
        value = cache.get('crimsononline.supercrisismode')
        
        if value is not None:
            url, response = value
        else:
            return None
        
        media_big = settings.MEDIA_URL
        media_url = media_big[len(settings.URL_BASE)-1:]
        media_url = media_url[:len(media_url)-1]
        
        if request.path[:6] == '/admin' or request.path[:11] == media_url:
            return None
        elif request.path != url:
            return HttpResponseRedirect(url)
        else:
            return HttpResponse(response)