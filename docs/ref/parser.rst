======
Parser
======

Asynchronous parsing with Celery
--------------------------------
For large rasters files the parsing step might take a while, so the html request that stored the raster might time out. To avoid this, django-raster can easily integrated with `Celery <http://celeryproject.org/>`_ .

To use celery for the raster parsing step, which is triggered automatically after saving RasterLayer instances, add the following setting to your django settings file::

        RASTER_USE_CELERY = True

If this setting is enabled, Celery pushes one task to the queue for each raster that is saved. The raster is then parsed upon execution of the task by a worker. The default of this setting is ``False``.

Pyramid building
----------------
Overview levels (or pyramids) are automatically created at the moment of importing the raster. The pyramid levels are aligned with the definition of a xyz style TMS service. Djago-raster will import the raster file in its original projection and flag those tiles with the ``is_base`` field. Subsequently a set of pyramids are created in the raster table. The pyramid is aligned with the XYZ tiles froma a tile map service, and will be accordingly indexed using the ``tilex``, ``tiley`` and ``tilez`` fields in the RasterTile table. The srid of the pyramid tiles is ``3857``.


Re-parsing data
---------------
Changing any of the fundamental settings such as the tile size will not automatically lead to an update for rasters that are already parsed. Only upon re-parsing of the rasters in the database, the data will be updated to the new values. When changing settings that change the raster tile structure, re-parse existing rasters to keep the database consistent. RasterLayers have a re-parse admin action to facilitate this.

