=======================
Ingesting raster layers
=======================
This section describes how to input raster data into a Django application
that has django-raster installed.

Creating Raster Layers
----------------------
Raster files can be uploaded through the admin interface and are stored the
RasterLayer model. Each raster file corresponds to one RasterLayer object. When
adding a new raster file, the following properties can be specified:

  - Layer name
  - Raster file
  - Data type (continuous, categorical, mask, or rank ordered)
  - SRID (optional)
  - Nodata value (optional)
  - Max zoom value (highest z-x-y zoom level to create tiles for, optional)

The srid, the nodata value and the maximum zoom value are all determined
automatically from the raster propreties if left blank.

Raster Tile Creation
--------------------
After uploading a file, django-raster automatically parses the raster file. The
parsing includes extraction of metadata for the raster and its bands and
creating tiles. The progess or possible errors in parsing is written to a parse
log object, which is exposed on the RasterLayer admin interface.

The parser automatically creates a tile pyramid in the z-x-y scheme of a TMS,
for all tile levels above the max zoom value. By default, the max zoom is
calculated automatically from the resolution of the raster. The zoom level
is set such that the resolution of the highest zoom is at least the original
resolution. This behavior can be changed by manually setting the highest zoom
level.

Asynchronous Parsing
^^^^^^^^^^^^^^^^^^^^
For most raster files, the creation of tiles takes several minutes or even
hours to complete. It is therefore highly recommended to configure the django
application with `Celery`__, to parse the rasters asynchronously. See also the
:doc:`installation` docs.

__ http://celeryproject.org
