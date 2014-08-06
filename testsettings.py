"""
Django settings for example project dev environment of raster app.
"""
import os
SECRET_KEY = 'testkey'

INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
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
