# Django settings for cualbondi project.
import os

CUALBONDI_ENV = os.environ.get('CUALBONDI_ENV', 'development')

DEBUG = os.environ.get('DEBUG', False)
TEMPLATE_DEBUG = DEBUG

ALLOWED_HOSTS = [os.environ.get('ALLOWED_HOSTS', '*')]

LOGIN_REDIRECT_URL = '/'

ABSOLUTE_URL_OVERRIDES = {
    'auth.user': lambda u: "/usuarios/%s/" % u.username, 
}

ADMINS = (
    # ('Your Name', 'your_email@example.com'),
)

DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'info@cualbondi.com.ar')

MANAGERS = ADMINS

BASE_PATH = os.path.dirname(os.path.abspath(__file__))

USE_CACHE = os.environ.get('USE_CACHE', True)

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.memcached.MemcachedCache',
        'LOCATION': os.environ.get('MEMCACHED_HOST', '127.0.0.1:11211'),
    }
}
CACHE_TIMEOUT = os.environ.get('CACHE_TIMEOUT', 60*60)

# Variables personalizadas
RADIO_ORIGEN_DEFAULT = 200
RADIO_DESTINO_DEFAULT = 200
LONGITUD_PAGINA = 5

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# On Unix systems, a value of None will cause Django to use the same
# timezone as the operating system.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'America/Argentina/Buenos_Aires'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'es-ar'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = False

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale
USE_L10N = True

# Absolute filesystem path to the directory that will hold user-uploaded files.
# Example: "/home/media/media.lawrence.com/media/"
MEDIA_ROOT = os.path.join(BASE_PATH, os.path.pardir, 'media')

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash.
# Examples: "http://media.lawrence.com/media/", "http://example.com/media/"
MEDIA_URL = 'media/'

# Absolute path to the directory static files should be collected to.
# Don't put anything in this directory yourself; store your static files
# in apps' "static/" subdirectories and in STATICFILES_DIRS.
# Example: "/home/media/media.lawrence.com/static/"
STATIC_ROOT = os.path.join(BASE_PATH, os.path.pardir, 'static')

# URL prefix for static files.
# Example: "http://media.lawrence.com/static/"
STATIC_URL = '/static/'

# URL prefix for admin static files -- CSS, JavaScript and images.
# Make sure to use a trailing slash.
# Examples: "http://foo.com/static/admin/", "/static/admin/".
ADMIN_MEDIA_PREFIX = '/static/admin/'

# Additional locations of static files
STATICFILES_DIRS = (
    # Put strings here, like "/home/html/static" or "C:/www/django/static".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
#    'django.contrib.staticfiles.finders.DefaultStorageFinder',
)

# Make this unique, and don't share it with anybody.
SECRET_KEY = '=tr&%05vw6&s4eoq)wdj(d&(56#cq@5k0b-c$^v6vr)#%e(c+&'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
)

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
)


TEMPLATE_CONTEXT_PROCESSORS = (
  'django.contrib.auth.context_processors.auth',
)

ROOT_URLCONF = 'urls'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
    os.path.join(os.path.dirname(__file__),'templates'),
)

GOOGLE_API = "//maps.google.com/maps/api/js?v=3.6&sensor=false"

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.admin',
    'django.contrib.gis',
    'django.contrib.flatpages',
    'django.contrib.sitemaps',

    # Externas
    'bootstrap_toolkit',
    'floppyforms',
    'imagekit',
    'leaflet',
    'piston',
    'rest_framework',
    'rest_framework_tracking',
    'django_nose',

    # Propias
    'apps.api2',
    'apps.api3',
    'apps.catastro',
    'apps.core',
)

REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': ('apps.api2.permissions.ReadOnly',),
    'PAGE_SIZE': 10,
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.LimitOffsetPagination',
}
if CUALBONDI_ENV != 'development':
    REST_FRAMEWORK['DEFAULT_RENDERER_CLASSES'] = (
        'rest_framework_jsonp.renderers.JSONPRenderer',
    )


# A sample logging configuration. The only tangible logging
# performed by this configuration is to send an email to
# the site admins on every HTTP 500 error.
# See http://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.
LOGGING = {
    'version': 1,
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse'
        }
    },
    'formatters': {
        'simple': {
            'format': '%(levelname)s | %(message)s'
        },
        'json': {
            '()': 'django_log_formatter_json.JSONFormatter',
        }
    },
    'handlers': {
        'mail_admins': {
            'level': 'ERROR',
            'filters': ['require_debug_false'],
            'class': 'django.utils.log.AdminEmailHandler'
        },
        'console':{
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'json'
        },
#        'file': {
#            'level': 'DEBUG',
#            'class': 'logging.FileHandler',
#            'filename': '/tmp/django.log',
#        }
    },
    'loggers': {
        'django.request': {
            'handlers': ['console'],
            'level': 'ERROR',
            'propagate': True,
        },
        'logstash': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': True
        }
    },
}

HOME_URL = os.environ.get('HOME_URL')

EMAIL_HOST = os.environ.get('EMAIL_HOST')
EMAIL_PORT = os.environ.get('EMAIL_PORT')

FACEBOOK_APP_ID = os.environ.get('FACEBOOK_APP_ID', '')
FACEBOOK_API_SECRET = os.environ.get('FACEBOOK_API_SECRET', '')
FACEBOOK_EXTENDED_PERMISSIONS = ['email']
SOCIAL_AUTH_FACEBOOK_KEY = os.environ.get('FACEBOOK_APP_ID', '')
SOCIAL_AUTH_FACEBOOK_SECRET = os.environ.get('FACEBOOK_API_SECRET', '')
SOCIAL_AUTH_FACEBOOK_SCOPE = ['email']


DATABASES = {
    'default': {
        'ENGINE': 'django.contrib.gis.db.backends.postgis',
        'NAME': os.environ.get('POSTGRES_DB', 'geocualbondidb'),
        'USER': os.environ.get('POSTGRES_USER', 'postgres'),
        'PASSWORD': os.environ.get('POSTGRES_PASSWORD', ''),
        'HOST': os.environ.get('DB_HOST', 'db')
    }
}

if CUALBONDI_ENV == 'development':
    DEBUG_TOOLBAR_PATCH_SETTINGS = False 
    INSTALLED_APPS += ('debug_toolbar', 'django_extensions')

if CUALBONDI_ENV == 'production':
    from settings_local import *
    INSTALLED_APPS += LOCAL_INSTALLED_APPS
