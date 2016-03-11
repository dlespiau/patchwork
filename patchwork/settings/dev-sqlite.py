"""
Quick development settings for patchwork project.

Most of these are commented out as they will be installation dependent.

Design based on:
    http://www.revsys.com/blog/2014/nov/21/recommended-django-project-layout/
"""

from __future__ import absolute_import

from .base import *  # noqa
from os.path import join, dirname

#
# Core settings
# https://docs.djangoproject.com/en/1.6/ref/settings/#core-settings
#

# Security
#
# You'll need to replace this to a random string. The following python code can
# be used to generate a secret key:
#
#      import string, random
#      chars = string.letters + string.digits + string.punctuation
#      print repr("".join([random.choice(chars) for i in range(0,50)]))

SECRET_KEY = '00000000000000000000000000000000000000000000000000'

# Database
#
# SQLite database is used for development.
# Please see https://docs.djangoproject.com/en/1.7/ref/settings/#databases
# for documentation about database configuration.

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': join(dirname(__file__), 'db.sqlite'),
    },
}

DEBUG = True
TEMPLATE_DEBUG = True
ENABLE_XMLRPC = True
