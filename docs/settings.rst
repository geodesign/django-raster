Settings
========
::

    RASTER_TILESIZE = 256

This setting defines the size of the tiles that the raster layer parser stores
in the database. It is not recommended to use this settings, as the X-Y-Z tile
endpoints only integrate well with javascript libraries (such as openlayers or 
leaflet) if the tile size is 256. Defaults to 256.::

    RASTER_ZOOM_NEXT_HIGHER = True

The raster layer parser automatically determines the scale of the input
rasters. This setting defines the hightest zoom level at which tiles are
created. By default, the next underlying zoomlevel is used. Set this to
``False`` if you only want to create tiles up to the next-higher zoomlevel.
Defaults to ``True``.::
    
    RASTER_USE_CELERY = False

Determines wether to use celery tasks for parsing raster layers. It is highly
recommended to configure celery, as raster parsing can take quite a while and
the parsing through normal web requests will often timed out, even for medium
sized raster.::

    RASTER_WORKDIR = None

Use this to specify a custom working directory used by the django-raster
package when parsing raster files. This is where intermediate files are stored.
Defaults to the default temporary directory of the machine.::

    RASTER_TILE_CACHE_TIMEOUT = 60 * 60 * 24

The tile out time for cached tiles. Set this to zero if you do not want to
chache tiles. Defaults to 1 day.
