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
TIME_ZONE = 'America/New_York'

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

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3', # Add 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': 'django.db',                      # Or path to database file if using sqlite3.
        'USER': '',                      # Not used with sqlite3.
        'PASSWORD': '',                  # Not used with sqlite3.
        'HOST': '',                      # Set to empty string for localhost. Not used with sqlite3.
        'PORT': '',                      # Set to empty string for default. Not used with sqlite3.
    }
}

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# Absolute path to the directory that holds media.
# Example: "/home/media/media.lawrence.com/"
MEDIA_ROOT = os.path.join(os.path.split(os.path.abspath(__file__))[0], 'media')
STATIC_ROOT = '/srv/crimson/static'
STATIC_URL = '/static/'
MEDIA_URL = '/media/'

STATICFILES_DIRS = (
    os.path.join(os.path.split(os.path.abspath(__file__))[0], 'static'),
)

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
#    'django.template.loaders.eggs.load_template_source',
)

# A tuple of callables that are used to populate the context in RequestContext
#defaults.TEMPLATE_CONTEXT_PROCESSORS += (
#    'crimsononline.content_module.context_processors.cm_processor',
#)

TEMPLATE_CONTEXT_PROCESSORS = (
    "django.contrib.auth.context_processors.auth",
    "django.core.context_processors.debug",
    "django.core.context_processors.i18n",
    "django.core.context_processors.media",
    "django.core.context_processors.static",
    "django.core.context_processors.tz",
    "django.contrib.messages.context_processors.messages"
)

MIDDLEWARE_CLASSES = (
    'django.middleware.gzip.GZipMiddleware',
    'django.middleware.cache.UpdateCacheMiddleware',
    'crimsononline.mware.linkscriptoptimizer.LinkScriptOptimizer',
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.doc.XViewMiddleware',
    'django.contrib.flatpages.middleware.FlatpageFallbackMiddleware',
    'crimsononline.mware.supercrisismode.SuperCrisisMode',
    'django.middleware.cache.FetchFromCacheMiddleware',
    'debug_toolbar.middleware.DebugToolbarMiddleware',
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
    'django.contrib.staticfiles',
    'crimsononline.content',
    'crimsononline.admin_cust',
    'crimsononline.content_module',
    'crimsononline.search',
    'crimsononline.common',
    'crimsononline.subscriptions',
    'crimsononline.mware',
    'crimsononline.promote',
    'debug_toolbar',
    'storages',
    'django_extensions',
    'south',
]

INTERNAL_IPS = ( )

try:
    import pysolr
    INSTALLED_APPS.append('haystack')
    HAYSTACK = True
except ImportError:
    HAYSTACK = False
finally:
    INSTALLED_APPS = tuple(INSTALLED_APPS)


MEDIA_LOC = MEDIA_ROOT

# Notifies the users in "to" whenever someone edits an article over "time_span" days old"
NOTIFY_ON_SKETCHY_EDIT = {
    "enabled": False,
    "from": "businessmanager@thecrimson.com",
    "to": ["president@thecrimson.com"],
    "subject": "Sketchy Article Change!",
    "time_span": 7, # In days
}


# specify SOLR options in local_settings.py
SEARCH_SORT_PARAMS = {
    "score desc": "Relevance",
    "date desc" : "Date" # Added date
}

HAYSTACK_SITECONF = 'crimsononline.search_sites'
HAYSTACK_SEARCH_ENGINE = 'solr'
HAYSTACK_SOLR_URL = 'http://localhost:8983/solr'
HAYSTACK_SOLR_TIMEOUT = 60*5

#DISQUS = not DEBUG # you can override this in localsettings.py
DISQUS = True
FLYBY_TIP_ADDRESS = "flybytips@thecrimson.com"

# caching durations in sec
CACHE_SHORT = 2 * 60 * 60
CACHE_STANDARD = 4 * 60 * 60
CACHE_LONG = 12 * 60 * 60
CACHE_EONS = 7 * 24 * 60 * 60

# break this out here to avoid circular import of urls.py
CONTENT_URL_RE = r'(?P<ctype>[\w\-]+)/(?P<year>\d{4})/(?P<month>\d{1,2})/' \
                  '(?P<day>\d{1,2})/(?P<slug>[0-9\w_\-%]+)/$'
CGROUP_URL_RE = r'(?P<gtype>[\w]+)/(?P<gname>[\w0-9\-]+)/'
CGROUP_FILTER_URL_RE = r'(page/(?P<page>\d+)/)?(tags/(?P<tags>[,\w&\'\s-]+)/)?'

if DEBUG:
    CACHE_BACKEND = 'dummy:///'
    CACHE_MIDDLEWARE_SECONDS = 5

try:
    from local_settings import *
except ImportError:
    pass
    
"""
import logging
logging.basicConfig(
    level = logging.DEBUG,
    format = '%(asctime)s %(levelname)s %(message)s',
    filename = '/tmp/myapp.log',
    filemode = 'w'
)
"""
