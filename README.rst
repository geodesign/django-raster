Rasters for Django
==================
Django-raster provides the simplest possible raster data integration for Django projects using a PostGIS database backend.

.. image:: https://api.shippable.com/projects/5423d57480088cee586cd0c8/badge?branchName=master
    :target: https://app.shippable.com/projects/5423d57480088cee586cd0c8/builds/latest

Setup
-----
**Note: This package requires a PostGIS >= 2.0**

1. Install package with ``pip install django-raster``

2. Add "raster" to your INSTALLED_APPS setting like this::

        INSTALLED_APPS = (
            ...
            'raster',
        )

3. Run ``python manage.py migrate`` to create the raster models.

4. (Optional) Add ``RASTER_USE_CELERY = True`` to your project's setting to enable asynchronous raster parsing.

Description
-----------
Django-raster provides the simplest possible integration of raster
data in Django. It is based on the python bindings provided by the `GDAL <https://pypi.python.org/pypi/GDAL/>`_ package. Raster files can be uploaded and parsed through the admin interface. The raw raster data can be parsed asynchronously if `Celery <http://celeryproject.org/>`_ is integrated into the Django project (see below).

Once a raster file is uploaded, the parser will extract the data in the raster file and store the rasters in regular tiles of 100x100 pixels in a PostGIS raster table. Each tile will be one row in a PostGIS raster table.

For this, the package defines two models and one field:

* ``RasterLayer`` - storing the raw raster files and meta-data (for example rasterfile=raster.tif and srid=4326)

* ``RasterTile`` - storing the parsed raster in PostGis. The raster data is split into tiles of 100x100 pixels and each tile is stored as an instance of RasterTile. The raster data itself is stored in a *RasterField* within the RasterTile model.

* ``RasterField`` - an extension of the Django `BinaryField` class to store the raster data. The only difference to the BinaryField class is that the *db_type* is redefined as *raster*, such that the data is stored as raster in PostGIS.

Due to the simplicity of the implementation, no spatial querying can be done on the raster data through python. This package is not integrated with GeoDjango and has none of the features that GeoDjango spatial models have. Proper integration of rasters into Geodjango with spatial querying etc. is beyond the scope of this package. If required however, custom SQL can be used to make spatial queries on the raster data.

Usage
-----
After setting the package up, you can upload raster files through the admin interface using the RasterLayer model. Specify a layer name, the raster data type (continuous, categorical, mask or rank ordered), the raster's srid, the nodata value and the raster file to be uploaded.

Upon saving the raster file, django-raster automatically loads the raster data from the file into a raster column in the PostGIS database. These tiles will be stored in the RasterTile model, which should not be edited directly but only through adding and deleting entire RasterLayers instances.

The RasterLayer instances have a *parse_log* field, which stores information about the parsing process. For debugging, there might be some useful information in the parse log.

Asynchronous parsing with Celery
--------------------------------
For large rasters files the parsing step might take a while, so the html request that stored the raster might time out. To avoid this, django-raster can easily integrated with `Celery <http://celeryproject.org/>`_ .

To use celery for the raster parsing step, which is triggered automatically after saving RasterLayer instances, add the following setting to your django settings file::

        RASTER_USE_CELERY = True

If this setting is enabled, Celery pushes one task to the queue for each raster that is saved. The raster is then parsed upon execution of the task by a worker. The default of this setting is ``False``.

Tile size
---------
The default tile size is 100x100 pixels. The tile size can be changed by providing an integer value in the ``RASTER_TILESIZE`` setting. The tiles are always saquares, so the tileize is set by one integer that specifies the number of pixels in each tile. For instance, setting::

        RASTER_TILESIZE = 200
        
will import the raster in tiles of 200x200 pixels. 

Pyramid building
----------------
Overview levels (or pyramids) are automatically created at the moment of importing the raster. The pyramid levels are stored in the ``levels`` field on the RasterTile model. By default, djago-raster will import the raster file in its original projection (as specified in the RasterLayer instance) and subsequently create a set of pyramids in the raster table. The original projection will be stored as Level ``0``, then the overview levels ``[1,2,4,8,16,32]`` will be computed and stored in tiles with increasing pixel scales. So level ``0`` is the original raster in its original scale, level ``1`` is the raster at the same scale but at a global projection (the default global projection is the "web mercator" EPSG ``3857``), and level ``16`` will aggregate ``16x16`` pixels to one. The size of one pixel is N times the original scale, where N is the overview level index.

The projection of the pyramid tiles can be changed to any valid EPSG code using the following setting::

        RASTER_GLOBAL_SRID = 3857

To change the overview levels that are computed, use following setting::

        RASTER_OVERVIEW_LEVELS = [1,2,4,8,16,32]

Raster padding
--------------
By default, the tiles on the edge of the raster file are padded such that all raster tiles for one rasterlayer are of the same size. If you dont want the raster tiles to be padded at the edges of the raster, you can disable padding through the following setting::

        RASTER_PADDING = False

Re-parsing data
---------------
Changing any of the fundamental settings (tile size, pyramid settings and padding) will not automatically lead to an update for rasters that are already parsed. Only upon re-parsing of the rasters in the database, the data will be updated to the new values. When changing settings that change the raster tile structure, re-parse existing rasters to keep the database consistent. RasterLayers have a re-parse admin action to facilitate this.

Value count functionality
-------------------------
The RasterLayer model has a method to calculate counts for categorical layers. This function only works with categorical or mask raster layers. It returns a count in pixels for each distinct raster pixel value in the polygon provided to the function. If no polygon is provided, the counts are performed on the entire raster layer. For example::

         mylayer = RasterLayer.objects.first()
         mylayer.value_count('POLYGON ((30 10, 40 40, 20 40, 10 20, 30 10))')
         >> [{'count': 90679, 'value': 5.0},
             {'count': 4252237, 'value': 1.0},
             {'count': 4752665, 'value': 2.0},
             {'count': 685432, 'value': 3.0},
             {'count': 153598, 'value': 9.0}]
