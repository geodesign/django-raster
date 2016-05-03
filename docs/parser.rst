=============
Raster Layers
=============
A :class:`RasterLayer` is django-raster's representation of raster files. It
can be used to input raster data into your application. The basic concept is
one ``RasterLayer`` for each raster file.

Storing a Raster File
---------------------
Raster files can be uploaded through the admin interface and are stored in the
:class:`RasterLayer` model. Each raster file corresponds to one
:class:`RasterLayer` object. When adding a new raster file, the following
properties are **required**:

  - Layer name
  - Raster file
  - Data type

The datatype tells django-raster how to interpret the pixel values. The choices
are continuous, categorical, mask, or rank ordered. By default, django-raster
extracts all other raster metadata from the input file. The **optional** input
parameters are the following

  - Description
  - SRID
  - Nodata value
  - Max zoom value
  - Legend


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
parser extracts metadata from the raster and its bands, and creates tiles. The
progess or possible errors in parsing is written to a parse log object, which
is exposed on the :class:`RasterLayer` admin interface.

The parser automatically creates a tile pyramid in the z-x-y scheme of a TMS.
By default, the highest zoom level for which to create tiles is calculated
automatically from the resolution of the raster. The zoom level is set such
that the resolution of the highest zoom is at least the original resolution.
This behavior can be changed by manually setting the highest zoom level, using
the ``max_zoom_value`` field.

The tiles are stored as :class:`RasterTile` objects. The raster data itself is
stored as PostGIS rasters through a `RasterField`__. The tiles are managed
automatically through their parent :class:`RasterLayer` object, and do normally
not require any manual user manipulation.

__ https://docs.djangoproject.com/en/1.9/ref/contrib/gis/model-api/#rasterfield

Asynchronous Parsing
^^^^^^^^^^^^^^^^^^^^
It is highly recommended to configure the Django application with `Celery`__,
to parse the rasters asynchronously.

The reason for this is that for most raster files, the creation of tiles takes
several minutes or even hours to complete. Since the parsing is triggered
automatically upon upload, the html requests in the admin will often time out.
For more information about how to configure Celery, consult the
:doc:`installation` section.

__ http://celeryproject.org
