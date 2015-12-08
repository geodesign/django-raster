============
Introduction
============

Description
-----------
Django-raster provides high level utilities to work with `raster data`__ in
Django. It is based on the Django internal `GDALRaster`_ object and
`RasterField`_ datatype.

There are three main components inb


Raster files can be uploaded and parsed through the admin interface. The raw
raster data can be parsed asynchronously if `Celery`__ is integrated into the
Django project (see below).

__ http://celeryproject.org
__ http://en.wikipedia.org/wiki/GIS_file_formats#Raster

Once a raster file is uploaded, the parser will extract the data in the raster
file and store the rasters in regular tiles of 256x256 pixels in a PostGIS
raster table. Each tile will be one row in a PostGIS raster table.

For this, the package defines two models and one field:

* ``RasterLayer`` - storing the raw raster files and meta-data (for example rasterfile=raster.tif and srid=4326)

* ``RasterTile`` - storing the parsed raster in PostGis. The raster data is split into tiles of 256x256 pixels and each tile is stored as an instance of RasterTile. The raster data itself is stored in a *RasterField* within the RasterTile model.

.. _RasterField: https://docs.djangoproject.com/en/dev/ref/contrib/gis/model-api/#rasterfield
.. _GDALRaster: https://docs.djangoproject.com/en/1.9/ref/contrib/gis/gdal/#raster-data-objects

Usage
-----
To add data, upload a raster file through the admin. Create a Legend object and call the tiles through the ``/raster/tiles/myrasterfile.tif/{z}/{x}/{y}.png`` url setup previously.


After setting the package up, raster files can be uploaded through the admin interface using the RasterLayer model. Specify a layer name, the raster data type (continuous, categorical, mask or rank ordered), the raster's srid, the nodata value and the raster file to be uploaded.

Upon saving the a RasterLayer instance with a raster file, django-raster automatically loads the raster data from the file into a raster field in the RasterTile model. The RasterLayer instances have a *parse_log* field, which stores information about the parsing process. For debugging, there might be some useful information in the parse log.

A simple TMS view is part of this package as well, to serve the tiles with dynamic symbology. The endpoint is briefly described below, it works as a ``{z}/{x}/{y}.png`` url.
