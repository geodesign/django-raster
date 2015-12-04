=====
Views
=====

TMS View
--------
Leveraging the img property of the rasters, a Tile Map Service (TMS) view is part of this package. The url can be included by::

        url(r'tiles/', include('raster.urls'))

The urlpattern will look for the filename of the raster to be shown, and xyz tiles in the RasterTiles table. A legend entry has to be created for the rasterlayer for any data to be shown. Any category that is not represented in the Legend will be invisible transparent pixels. An example request would be::

        /tile/myraster.tif/9/141/216.png

For use in javascript libraries such as leaflet or openlayers, the TMS enpoint for one rasterlayer can be included using::

        var layer = new L.tileLayer(/tiles/myraster.tif/{z}/{x}/{y}.png)

By default, the TMS view is cached for 24 hours, to change the timeout of the cache use the ``RASTER_TILE_CACHE_TIMEOUT`` setting. To disable caching, set this timeout to 0.
