=============
Raster Layers
=============
A :class:`RasterLayer` is django-raster's representation of raster files. It
can be used to input raster data into your application. In most cases there is
one :class:`RasterLayer` for each raster file.

Storing a Raster File
---------------------
Raster files can be uploaded through the admin interface and are stored in the
:class:`RasterLayer` model. Like for any other model, raster layers can also be
created using the Django shell. Each raster file corresponds to one
:class:`RasterLayer` object. When adding a new raster file, the following
properties are **required**:

  - Layer name
  - Raster file (either as file, http url or s3 url)
  - Data type

The datatype tells django-raster how to interpret the pixel values. The choices
are "continuous", "categorical", "mask", or "rank ordered". By default,
django-raster extracts all other raster metadata from the input file. The
**optional** input parameters are the following

  - Description
  - SRID
  - Nodata value
  - Max zoom value
  - Legend

The srid, the nodata value and the maximum zoom value are all determined
automatically from the raster properties if left blank. The max zoom value
specifies the highest z-x-y zoom level to create tiles for (see below).

The legend attribute is a foreign key to a raster :class:`Legend` object. If
the raster legend is specified, it is used as default style when rendering
tiles from that raster. How raster tiles are rendered is described in detail in
the :doc:`tms` section.

There are also three boolean flags that allow finer grained control over the
raster layer parse process.

  - Next higher zoom level
  - Build pyramids
  - Store reprojected

The raster layer is "snapped" to the next higher zoom level by default. To
snap the raster to the next lower zoom level when compared to the true
resolution of the data, the "next higher" flag has to be disactivated.

There is a "build pyramids" flag that controls whether the tiles should be created
also for the lower zoom levels. This is enabled by default and is recommended
in most cases as the tile renderer will expect those tiles to be present.

During parsing, the raster is reprojected to the web mercator projection. This
operation is costly and is only done once by default. Django-raster stores a
reprojected version in a separate model. To prevent the storage of the
reprojected file, the "store reprojected" flag can be disactivated. Note that
this will result in less use of storage, but an overhead when parsing,
especially for asynchronous parsing where the file will be reprojected by each
worker.

Specifying an Url as Source
^^^^^^^^^^^^^^^^^^^^^^^^^^^
The raster file can be uploaded directly using the raster file field, or passed
as a url either to a public http(s) address, or a url like string, pointing
directly to an s3 bucket. The http(s) urls are regular web urls.

For the s3 links, the ``boto3`` library is used to directly access an s3 bucket
and download it from there. In this way, private or requester-pays buckets can
be used as source. The credentials for accessing the buckets need to be configured
so that boto3 can see them.

The url should have the following structure

::

    s3://BUCKET_NAME/BUCKET_KEY

for instance,

::

    s3://sentinel-s2-l1c/tiles/12/S/VG/2017/9/15/0/B12.jp2

gets the same file as the following regular http url

::

    http://sentinel-s2-l1c.s3.amazonaws.com/tiles/12/S/VG/2017/9/15/0/B12.jp2

but instead of making a regular web request, it accesses the file using boto3.

Note that for requester pays bucket this might incur charges even if the
requester is not the owner of the bucket.

Raster Tile Creation
--------------------
Upon uploading a file, django-raster automatically parses the raster file. The
parser extracts metadata from the raster and its bands, and creates tiles. The
progress or possible errors in parsing is written to a parse log object, which
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
to parse the rasters asynchronously. For most raster files, the creation of
tiles takes several minutes or even hours to complete. Since the parsing is
triggered automatically upon upload, the html requests in the admin will often
time out. For more information about how to configure Celery, consult the
:doc:`installation` section.

__ http://celeryproject.org
