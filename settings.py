"""
Settings for django-raster tests
"""

import os
SECRET_KEY = 'testkey'

INSTALLED_APPS = (
    'raster'
)

DATABASES = {
    'default': {
        'ENGINE':   'django.contrib.gis.db.backends.postgis',
        'USER':     'postgres',
        'HOST':     'localhost',
        'NAME':     os.environ.get('DB_NAME', '')
    }
}
