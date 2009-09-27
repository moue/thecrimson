from django.core.cache import cache
from django.http import HttpResponse, HttpResponseRedirect
from django.db import models
from crimsononline.content.models import Content

#Checks the cache to see if we have entered SUPER CRISIS MODE
#If so, it redirects all other requests to the home page, and 
#for homepage requests it renders a single article that is
#defined in the admin interface
class SuperCrisisMode(object):
	def process_request(self, request):
		if request.path == '/supercrisis/':
			test_tuple = '/crisis/', 'Your Mom!'
			#print test_tuple
			cache.set('crimsononline.supercrisismode', test_tuple, 1000000)
			
		if request.path == '/supercrisisoff/':
			cache.set('crimsononline.supercrisismode', None, 1000000)
			
		value = cache.get('crimsononline.supercrisismode')
		if value is not None:
			url, response = value
		else:
			return None
		
		if request.path[:6] == '/admin' and request.path[:11] != '/site_media':
			return None
		elif request.path != url:
			return HttpResponseRedirect(url)
		else:
			return HttpResponse(response)