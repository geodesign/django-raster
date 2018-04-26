from __future__ import unicode_literals

from django.conf.urls import url
from raster.views import AlgebraView, ExportView, LegendView

urlpatterns = [

    # Normal raster tiles endpoint
    url(
        r'^tiles/(?P<layer>[^/]+)/(?P<z>[0-9]+)/(?P<x>[0-9]+)/(?P<y>[0-9]+).(?P<frmt>png|jpg|tif)$',
        AlgebraView.as_view(),
        name='tms',
    ),

    # Raster algebra endpoint
    url(
        r'^algebra/(?P<z>[0-9]+)/(?P<x>[0-9]+)/(?P<y>[0-9]+).(?P<frmt>jpg|png|tif)$',
        AlgebraView.as_view(),
        name='algebra',
    ),

    # Pixel value endpoint
    url(
        r'^pixel/(?P<xcoord>-?\d+(?:\.\d+)?)/(?P<ycoord>-?\d+(?:\.\d+)?)$',
        AlgebraView.as_view(),
        name='pixel',
    ),

    # Raster legend endpoint
    url(
        r'^legend(?:/(?P<legend_id>[^/]+))?/$',
        LegendView.as_view(),
        name='legend',
    ),

    # Exporter endpoint
    url(
        r'^export$',
        ExportView.as_view(),
        name='export',
    ),
]
