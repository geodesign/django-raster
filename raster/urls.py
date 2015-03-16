from django.conf import settings
from django.conf.urls import patterns, url
from django.views.decorators.cache import cache_page

from raster.views import TmsView, legend

if hasattr(settings, 'RASTER_TILE_CACHE_TIMEOUT'):
    cache_timeout = settings.RASTER_TILE_CACHE_TIMEOUT
else:
    cache_timeout = 60*60*24

urlpatterns = patterns('',

    # Url to request raster tiles
    url(r'^tiles/(?P<layer>[^/]+)/(?P<z>[0-9]+)/(?P<x>[0-9]+)/(?P<y>[0-9]+)(?P<format>\.jpg|\.png)$',
        cache_page(cache_timeout)(TmsView.as_view()),
        name='tms'),

    # Url to return legend as a json array (list of legend entries)
    url(r'^legend/(?P<layer_or_legend_name>[^/]+)$',
        cache_page(cache_timeout)(legend),
        name='legend'),
)
