from django.conf import settings
from django.conf.urls import patterns, url
from django.views.decorators.cache import cache_page

from raster.views import tms

if hasattr(settings, 'RASTER_TILE_CACHE_TIMEOUT'):
    cache_timeout = settings.RASTER_TILE_CACHE_TIMEOUT
else:
    cache_timeout = 60*60*24

urlpatterns = patterns('',
    url(r'^(?P<layers>[^/]+)/(?P<z>[0-9]+)/(?P<x>[0-9]+)/(?P<y>[0-9]+)(?P<format>\.jpg|\.png)$',
        cache_page(cache_timeout)(tms),
        name='tms'),
)
