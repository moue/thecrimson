from django.core.cache import cache
from django.http import HttpResponse

#Checks the cache to see if we have entered SUPER CRISIS MODE
#If so, it redirects all other requests to the home page, and 
#for homepage requests it renders a single article that is
#defined in the admin interface
class SuperCrisisMode(object):
	def process_request(self, request):
		if request.path == '/supercrisis/':
			print 'yourmom'
			cache.set('crimsononline.supercrisismode', 'Your Mom!', 1000000)
			print cache.get('crimsononline.supercrisismode')
			
		value = cache.get('SuperCrisisMode')
		print value
		if value != None and request.path != '/':
			return HttpResponse(value)
		else:
			return None