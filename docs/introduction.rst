============
Introduction
============
Django-raster provides high level utilities to work with `raster data`__ in
Django. It is based on the Django internal `GDALRaster`_ object and
`RasterField`_ datatype.

There are three main components in this package:

* A parser utility to ingest rasters through the admin.
* Tile map service endpoint to render raster data.
* Raster calculator to compute and render raster calculator expressions.

Raster files can be uploaded and parsed through the admin interface. The raw
raster data can be parsed asynchronously if `Celery`__ is integrated into the
Django project.

__ http://en.wikipedia.org/wiki/GIS_file_formats#Raster
__ http://celeryproject.org

Once a raster file is uploaded, the raster parser will automatically extract
the data in the raster and store it as PostGIS raster tiles on the database.

After ingesting the data, raster styles can be defined through the admin
interface which are then used to render the data through TMS endpoints. The
endpoints can be used in javascript mapping software such as OpenLayers or
Leaflet.

Limitations
-----------
The main limitation of the django-raster package is that it is focused on
single band rasters. For most of the functionality, only the first band in
the raster is used. While the tile parser processes and stores all bands of
the input rasters, for the TMS endpoints, currently only the first band is
used.

Another limitation is that the projection of the raster tiles is fixed to
the web mercator projection (EPSG 3857). This is because a large part of 
online mapping uses this projection, and especially TMS services.

.. _RasterField: https://docs.djangoproject.com/en/1.9/ref/contrib/gis/model-api/#rasterfield
.. _GDALRaster: https://docs.djangoproject.com/en/1.9/ref/contrib/gis/gdal/#raster-data-objects
