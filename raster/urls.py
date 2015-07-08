from django.conf import settings
from django.conf.urls import url
from django.views.decorators.cache import cache_page
from raster.views import AlgebraView, LegendView, TmsView

if hasattr(settings, 'RASTER_TILE_CACHE_TIMEOUT'):
    cache_timeout = settings.RASTER_TILE_CACHE_TIMEOUT
else:
    cache_timeout = 60 * 60 * 24

urlpatterns = [

    # Url to request raster tiles
    url(r'^tiles/(?P<layer>[^/]+)/(?P<z>[0-9]+)/(?P<x>[0-9]+)/(?P<y>[0-9]+)(?P<format>\.jpg|\.png)$',
        cache_page(cache_timeout)(TmsView.as_view()),
        name='tms'),

    url(r'^algebra/(?P<z>[0-9]+)/(?P<x>[0-9]+)/(?P<y>[0-9]+)(?P<format>\.jpg|\.png)$',
        cache_page(cache_timeout)(AlgebraView.as_view()),
        name='algebra'),

    # Url to return legend as a json array (list of legend entries)
    url(r'^legend/(?P<layer_or_legend_name>[^/]+)$',
        cache_page(cache_timeout)(LegendView.as_view()),
        name='legend'),
]
