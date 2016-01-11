============
Introduction
============
Django-raster provides high level utilities to work with `raster data`__ in
Django. It is based on the Django internal `GDALRaster`_ object and
`RasterField`_ datatype.

There are three main components in this package:

* Raster parser utility and admin.
* Tile map service endpoint to render raster data.
* Raster calculator to compute and render raster calculator expressions.

Raster files can be uploaded and parsed through the admin interface. The raw
raster data can be parsed asynchronously if `Celery`__ is integrated into the
Django project.

__ http://en.wikipedia.org/wiki/GIS_file_formats#Raster
__ http://celeryproject.org

Once a raster file is uploaded, the raster parser will automatically extract
the data in the raster and store it as PostGIS raster tiles on the database.

After ingesting the data, legends can be created through the admin interface
which are then used to render the data through TMS endpoints. The endpoints
can be used in javascript mapping software such as OpenLayers or Leaflet.

Once the layer is created in the database, the tiles can automatically be
accessed through an url similar to this::

    /raster/tiles/layer_id/{z}/{x}/{y}.png

.. _RasterField: https://docs.djangoproject.com/en/1.9/ref/contrib/gis/model-api/#rasterfield
.. _GDALRaster: https://docs.djangoproject.com/en/1.9/ref/contrib/gis/gdal/#raster-data-objects
