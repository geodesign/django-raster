Settings
========
A list of available settings to customize django-raster's behavior.

Asynchronous raster parsing
---------------------------
Determines wether to use celery tasks for parsing raster layers. It is highly
recommended to configure celery, as raster parsing can take quite a while and
the parsing through normal web requests will often timed out, even for medium
sized raster.
::

    RASTER_USE_CELERY = False

Maximum zoom levels for tile creation
-------------------------------------
The raster layer parser automatically determines the scale of the input
rasters. This setting defines the hightest zoom level at which tiles are
created. By default, the next underlying zoomlevel is used. Set this to
``False`` if you only want to create tiles up to the next-higher zoomlevel.
Defaults to ``True``.
::

    RASTER_ZOOM_NEXT_HIGHER = True

Parser working directory
------------------------
Use this to specify a custom working directory used by the django-raster
package when parsing raster files. This is where intermediate files are stored.
Defaults to the normal temporary directory of the machine.
::

    RASTER_WORKDIR = None

Tile Cache Timeout
------------------
The tile out time for cached tiles. Set this to zero if you do not want to
chache tiles. Defaults to 1 day.
::

    RASTER_TILE_CACHE_TIMEOUT = 60 * 60 * 24
