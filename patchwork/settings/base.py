"""
Base settings for patchwork project.
"""

import os

ROOT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        os.pardir, os.pardir)

#
# Core settings
# https://docs.djangoproject.com/en/1.6/ref/settings/#core-settings
#

# Models

INSTALLED_APPS = [
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.admin',
    'django.contrib.staticfiles',
    'patchwork',
    'rest_framework',
    'django_filters',
]

# HTTP

MIDDLEWARE_CLASSES = [
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'patchwork.threadlocalrequest.ThreadLocalRequestMiddleware',
    'patchwork.middleware.AccessControlAllowOriginMiddleware',
    'django.contrib.auth.middleware.SessionAuthenticationMiddleware',
]

MIDDLEWARE_CLASSES.append(
    'django.contrib.admindocs.middleware.XViewMiddleware')

# Globalization

TIME_ZONE = 'Australia/Canberra'

LANGUAGE_CODE = 'en-au'

USE_I18N = True

# Testing

TEST_RUNNER = 'django.test.runner.DiscoverRunner'

# URLs

ROOT_URLCONF = 'patchwork.urls'

# Templates

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(ROOT_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.contrib.auth.context_processors.auth',
                'django.template.context_processors.debug',
                'django.template.context_processors.i18n',
                'django.template.context_processors.media',
                'django.template.context_processors.static',
                'django.template.context_processors.tz',
                'django.contrib.messages.context_processors.messages',
                'patchwork.context_processors.settings',
                'patchwork.context_processors.site',
                'patchwork.context_processors.bundle',
            ],
        },
    },
]


# Email

DEFAULT_FROM_EMAIL = 'Patchwork <patchwork@patchwork.example.com>'
SERVER_EMAIL = DEFAULT_FROM_EMAIL

#
# Auth settings
# https://docs.djangoproject.com/en/1.6/ref/settings/#auth
#

LOGIN_URL = 'auth_login'
LOGIN_REDIRECT_URL = 'user'


#
# Sites settings
# https://docs.djangoproject.com/en/1.6/ref/settings/#sites
#

SITE_ID = 1


#
# Static files settings
# https://docs.djangoproject.com/en/1.6/ref/settings/#static-files
#

STATIC_URL = '/static/'

STATICFILES_DIRS = [
    os.path.join(ROOT_DIR, 'htdocs'),
]


#
# REST framework
#

REST_FRAMEWORK = {
}


#
# Celery
#

BROKER_URL = 'redis://localhost:6379'
CELERY_RESULT_BACKEND = 'redis://localhost:6379'
CELERY_ACCEPT_CONTENT = ['application/json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
# This timezone is used for time of periodic tasks, defaults to UTC.
# CELERY_TIMEZONE = 'Australia/Canberra'

#
# Patchwork settings
#

DEFAULT_PATCHES_PER_PAGE = 100

CONFIRMATION_VALIDITY_DAYS = 7

NOTIFICATION_DELAY_MINUTES = 10
NOTIFICATION_FROM_EMAIL = DEFAULT_FROM_EMAIL

# Set to True to enable the Patchwork XML-RPC interface
ENABLE_XMLRPC = False

# Set to True to enable redirections or URLs from previous versions
# of patchwork
COMPAT_REDIR = True

# Set to True to always generate https:// links instead of guessing
# the scheme based on current access. This is useful if SSL protocol
# is terminated upstream of the server (e.g. at the load balancer)
FORCE_HTTPS_LINKS = False
