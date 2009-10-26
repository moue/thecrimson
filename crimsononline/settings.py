# Django settings for crimsononline project.

# FOR THE SITE TO WORK, YOU NEED TO CREATE A LOCAL SETTINGS FILE FIRST
#  you can use the 'sample_local_settings.py' to help you out

import os

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
AUTH_PROFILE_MODULE = 'admin_cust.UserData'

AUTHENTICATION_BACKENDS = ('crimsononline.content.admin.HUIDBackend',
                           #'crimsononline.subscriptions.admin.SubscriberBackend',
                           'django.contrib.auth.backends.ModelBackend',)

# Language code for this installation. All choices can be found here:
# http://www.w3.org/TR/REC-html40/struct/dirlang.html#langcodes
# http://blogs.law.harvard.edu/tech/stories/storyReader$15
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

ADMINS = (
    # ('Your Name', 'your_email@domain.com'),
)

MANAGERS = ADMINS

DATABASE_ENGINE = 'sqlite3'           # 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'ado_mssql'.
DATABASE_NAME = 'db'             # Or path to database file if using sqlite3.
DATABASE_USER = ''             # Not used with sqlite3.
DATABASE_PASSWORD = ''         # Not used with sqlite3.
DATABASE_HOST = ''             # Set to empty string for localhost. Not used with sqlite3.
DATABASE_PORT = ''             # Set to empty string for default. Not used with sqlite3.

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = False

URL_BASE = 'http://localhost:8000/'

# Absolute path to the directory that holds media.
# Example: "/home/media/media.lawrence.com/"
MEDIA_ROOT = os.path.join(os.path.split(os.path.abspath(__file__))[0], 'static')

# URL that handles the media served from MEDIA_ROOT.
# Example: "http://media.lawrence.com"
MEDIA_URL = URL_BASE + 'site_media/'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.load_template_source',
    'django.template.loaders.app_directories.load_template_source',
#    'django.template.loaders.eggs.load_template_source',
)

# A tuple of callables that are used to populate the context in RequestContext
#defaults.TEMPLATE_CONTEXT_PROCESSORS += (
#    'crimsononline.content_module.context_processors.cm_processor',
#)

TEMPLATE_CONTEXT_PROCESSORS = (
    'django.core.context_processors.auth',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.cache.UpdateCacheMiddleware',
    #'crimsononline.mware.linkscriptoptimizer.LinkScriptOptimizer',
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.middleware.doc.XViewMiddleware',
    'django.contrib.flatpages.middleware.FlatpageFallbackMiddleware',
	'crimsononline.mware.supercrisismode.SuperCrisisMode',
    'django.middleware.cache.FetchFromCacheMiddleware',
)

ROOT_URLCONF = 'crimsononline.urls'

PROJECT_PATH = os.path.abspath(os.path.dirname(__file__))

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
    os.path.join(PROJECT_PATH, 'templates'),
)

INSTALLED_APPS = [
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.admin',
    'django.contrib.sites',
    'django.contrib.sitemaps',
    'django.contrib.flatpages',
    'crimsononline.content',
    'crimsononline.admin_cust',
    'crimsononline.content_module',
    'crimsononline.search',
    'crimsononline.common',
    'crimsononline.subscriptions',
	'crimsononline.mware',
]
try:
    import pysolr
    INSTALLED_APPS.append('haystack')
    HAYSTACK = True
except ImportError:
    HAYSTACK = False
finally:
    INSTALLED_APPS = tuple(INSTALLED_APPS)


MEDIA_LOC = MEDIA_ROOT
    
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_HOST_USER = 'crimsononlinemailer'
EMAIL_HOST_PASSWORD = 'abomination'
EMAIL_PORT = 587
EMAIL_USE_TLS = True

# specify SOLR options in local_settings.py
SEARCH_SORT_PARAMS = {
    "score desc": "Relevance",
    "date desc" : "Date" # Added date
}

HAYSTACK_SITECONF = 'crimsononline.search_sites'
HAYSTACK_SEARCH_ENGINE = 'solr'
HAYSTACK_SOLR_URL = 'http://127.0.0.1:8983/solr'

#DISQUS = not DEBUG # you can override this in localsettings.py
DISQUS = True

# caching durations in sec
CACHE_SHORT = 2 * 60 * 60
CACHE_STANDARD = 12 * 60 * 60
CACHE_LONG = 24 * 60 * 60
CACHE_EONS = 7 * 24 * 60 * 60

if DEBUG:
    CACHE_BACKEND = 'dummy:///'
    CACHE_MIDDLEWARE_SECONDS = 5

try:
    from local_settings import *
except ImportError:
    pass

