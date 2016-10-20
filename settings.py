"""
Settings for django-raster tests.
"""
from __future__ import unicode_literals

import os

SECRET_KEY = 'testkey'

INSTALLED_APPS = (
    'django.contrib.sessions',
    'raster',
    'django_nose',
)


MIDDLEWARE_CLASSES = [
    'django.contrib.sessions.middleware.SessionMiddleware',
]

DATABASES = {
    'default': {
        'ENGINE': 'django.contrib.gis.db.backends.postgis',
        'USER': os.environ.get('DB_USER', 'postgres'),
        'HOST': os.environ.get('DB_HOST', 'localhost'),
        'NAME': os.environ.get('DB_NAME', 'postgres'),
        'PASSWORD': os.environ.get('DB_PASSWORD', ''),
        'PORT': os.environ.get('DB_PORT', '5432')
    }
}

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'APP_DIRS': True,
    },
]

if 'USE_NOSE' in os.environ:
    TEST_RUNNER = 'django_nose.NoseTestSuiteRunner'
    NOSE_ARGS = [
        '--with-coverage',
        '--cover-package=raster',
    ]

ROOT_URLCONF = 'raster.urls'

RASTER_TILESIZE = 256
RASTER_USE_CELERY = True
CELERY_ALWAYS_EAGER = True
CELERY_EAGER_PROPAGATES_EXCEPTIONS = True
