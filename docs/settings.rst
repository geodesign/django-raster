========
Settings
========
A list of available settings to customize django-raster's behavior.

Asynchronous raster parsing
---------------------------
Determines whether to use celery tasks for parsing raster layers. It is highly
recommended to configure celery, as raster parsing can take quite a while and
the parsing through normal web requests will often timed out, even for medium
sized raster.
::

    RASTER_USE_CELERY = False

Parser working directory
------------------------
Use this to specify a custom working directory used by the django-raster
package when parsing raster files. This is where intermediate files are stored.
Defaults to the normal temporary directory of the machine.
::

    RASTER_WORKDIR = None


All in one parse task
---------------------
For some applications where the size of the rasters is small, the distributed
raster parsing might have more overhead than gain. The distributed parsing can
be disactivated with the following setting. If it is set to ``True``, rasters
are parsed in single celery tasks.
::

    RASTER_PARSE_SINGLE_TASK = True

Tile Cache Timeout
------------------
The tile out time for cached tiles. Set this to zero if you do not want to
chache tiles. Defaults to 1 day.
::

    RASTER_TILE_CACHE_TIMEOUT = 60 * 60 * 24
