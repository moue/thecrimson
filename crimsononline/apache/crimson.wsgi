import os
import sys

os.environ['DJANGO_SETTINGS_MODULE'] = 'crimsononline.settings'
sys.path.append('/home/sites/crimson/')

import django.core.handlers.wsgi
application = django.core.handlers.wsgi.WSGIHandler()
