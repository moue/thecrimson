# Django settings for crimsononline project.

# FOR THE SITE TO WORK, YOU NEED TO CREATE A LOCAL SETTINGS FILE FIRST
#  you can use the 'sample_local_settings.py' to help you out

from os import path
try:
    from local_settings import *
except:
    print """
	***********************************
	You need a local_settings.py file. 
	Check settings.py for more info.
	***********************************
	"""
    raise ImportError
import django.conf.global_settings as defaults

DEBUG = True
TEMPLATE_DEBUG = DEBUG

# Local time zone for this installation. Choices can be found here:
# http://www.postgresql.org/docs/8.1/static/datetime-keywords.html#DATETIME-TIMEZONE-SET-TABLE
# although not all variations may be possible on all operating systems.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'America/Chicago'

# Auth Profile (Contributor)
# *********** THIS IS BROKEN RIGHT NOW *************
AUTH_PROFILE_MODULE = 'content.UserData'

AUTHENTICATION_BACKENDS = ('django.contrib.auth.backends.ModelBackend',
                           'crimsononline.content.admin.HUIDBackend',)

# Language code for this installation. All choices can be found here:
# http://www.w3.org/TR/REC-html40/struct/dirlang.html#langcodes
# http://blogs.law.harvard.edu/tech/stories/storyReader$15
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = False

# Absolute path to the directory that holds media.
# Example: "/home/media/media.lawrence.com/"
try:
    MEDIA_ROOT
except:
    MEDIA_ROOT = path.join(path.split(path.abspath(__file__))[0], 'static')

# URL that handles the media served from MEDIA_ROOT.
# Example: "http://media.lawrence.com"
try:
    MEDIA_URL
except:
    MEDIA_URL = URL_BASE + 'site_media/'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
#    'django.template.loaders.filesystem.load_template_source',
    'django.template.loaders.app_directories.load_template_source',
#    'django.template.loaders.eggs.load_template_source',
)

# A tuple of callables that are used to populate the context in RequestContext
#defaults.TEMPLATE_CONTEXT_PROCESSORS += (
#    'crimsononline.content_module.context_processors.cm_processor',
#)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.middleware.doc.XViewMiddleware',
    'django.contrib.flatpages.middleware.FlatpageFallbackMiddleware',
    'crimsononline.mware.linkscriptoptimizer.LinkScriptOptimizer',
)

ROOT_URLCONF = 'crimsononline.urls'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.

    #os.path.join(os.path.dirname(__file__), 'templates').replace('\\','/'),
    path.join(path.dirname(__file__), 'templ/templatetags/templates').replace('\\','/'),
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.admin',
    'django.contrib.admindocs',
    'django.contrib.sites',
    'django.contrib.flatpages',
    'crimsononline.content',
    'crimsononline.admin_cust',
    'crimsononline.content_module',
    'crimsononline.search',
    'crimsononline.common',
    'crimsononline.subscriptions',
)

MEDIA_LOC = MEDIA_ROOT

try:
    import tagging
    FORCE_LOWERCASE_TAGS = True
except:
    pass