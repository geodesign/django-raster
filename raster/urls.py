from __future__ import unicode_literals

from django.conf import settings
from django.conf.urls import url
from django.views.decorators.cache import cache_page
from raster.views import AlgebraView, ExportView, LegendView

if hasattr(settings, 'RASTER_TILE_CACHE_TIMEOUT'):
    cache_timeout = settings.RASTER_TILE_CACHE_TIMEOUT
else:
    cache_timeout = 60 * 60 * 24

urlpatterns = [

    # Normal raster tiles endpoint
    url(
        r'^tiles/(?P<layer>[^/]+)/(?P<z>[0-9]+)/(?P<x>[0-9]+)/(?P<y>[0-9]+).(?P<frmt>png|jpg)$',
        cache_page(cache_timeout)(AlgebraView.as_view()),
        name='tms'
    ),

    # Raster algebra endpoint
    url(
        r'^algebra/(?P<z>[0-9]+)/(?P<x>[0-9]+)/(?P<y>[0-9]+).(?P<frmt>jpg|png)$',
        cache_page(cache_timeout)(AlgebraView.as_view()),
        name='algebra'
    ),

    # Raster legend endpoint
    url(
        r'^legend(?:/(?P<legend_id>[^/]+))?/$',
        cache_page(cache_timeout)(LegendView.as_view()),
        name='legend'
    ),

    # Exporter endpoint
    url(
        r'^export$',
        cache_page(cache_timeout)(ExportView.as_view()),
        name='export'
    ),
]
