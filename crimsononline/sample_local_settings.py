from os import path

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

# Make this unique, and don't share it with anybody.
SECRET_KEY = 'pick_50_random_chars_3oif3jfawfjpj8FJ#F$IOF2392!#t'

# keep this for local dev servers
URL_BASE = 'http://localhost:8000/'

# Absolute path to the directory that holds media.
# Example: "/home/media/media.lawrence.com/"
MEDIA_ROOT = path.join(path.split(path.abspath(__file__))[0], 'static')

# URL that handles the media served from MEDIA_ROOT.
# Example: "http://media.lawrence.com"
MEDIA_URL = URL_BASE + 'site_media/'

# If you want search to work with solr, specify the path of your solr installation
SOLR_ROOT = 'c:/web/solr/'

DISQUS_USER_KEY = ""
DISQUS_FORUM_KEY = ""
DISQUS_FORUM_ID = ""

GOOGLE_API_KEY = ""
