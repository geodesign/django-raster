=============
Raster Layers
=============
A :class:`RasterLayer` is django-raster's representation of raster files. It
can be used to input raster data into your application.

Storing a Raster File
---------------------
Raster files can be uploaded through the admin interface and are stored the
:class:`RasterLayer` model. Each raster file corresponds to one
:class:`RasterLayer` object. When adding a new raster file, the following
properties can be specified:

  - Layer name
  - Raster file
  - Data type
  - Description (optional)
  - SRID (optional)
  - Nodata value (optional)
  - Max zoom value (optional)
  - Legend (optional)

The datatype tells django-raster how to interpret the pixel values. The choices
are continuous, categorical, mask, or rank ordered.

The srid, the nodata value and the maximum zoom value are all determined
automatically from the raster propreties if left blank. The max zoom value
specifies the highest z-x-y zoom level to create tiles for (see below).

The legend attribute is a foreign key to a raster :class:`Legend` object. If
the raster legend is specified, it is used as default style when rendering
tiles from that raster. How raster tiles are rendered is described in detail in
the :doc:`tms` section.

Raster Tile Creation
--------------------
Upon uploading a file, django-raster automatically parses the raster file. The
parsing includes extraction of metadata for the raster and its bands and
creating tiles. The progess or possible errors in parsing is written to a parse
log object, which is exposed on the :class:`RasterLayer` admin interface.

The parser automatically creates a tile pyramid in the z-x-y scheme of a TMS,
for all tile levels above the max zoom value. By default, the max zoom is
calculated automatically from the resolution of the raster. The zoom level
is set such that the resolution of the highest zoom is at least the original
resolution. This behavior can be changed by manually setting the highest zoom
level.

The tiles are stored as PostGIS rasters in the database using the django-raster
internal :class:`RasterTile` model. The data is stored in a `RasterField`__. The tiles are managed
automatically through their parent :class:`RasterLayer` object, and do normally
not require user manipulation.

__ https://docs.djangoproject.com/en/1.9/ref/contrib/gis/model-api/#rasterfield

Asynchronous Parsing
^^^^^^^^^^^^^^^^^^^^
For most raster files, the creation of tiles takes several minutes or even
hours to complete. Since the parsing is triggered automatically upon upload,
the html requests in the admin will often time out.

It is therefore highly recommended to configure the Django application with
`Celery`__, to parse the rasters asynchronously. See also the
:doc:`installation` docs.

__ http://celeryproject.org
