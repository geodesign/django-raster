Rasters for Django
==================
Django-raster provides basic raster data integration for Django projects with a PostGIS database backend.


Setup
-----
**Note: This package requires a PostGIS >= 2.0**

1. Install package with ``pip install django-raster``

2. Add "raster" to your INSTALLED_APPS setting like this::

        INSTALLED_APPS = (
            ...
            'raster',
        )

3. Run ``python manage.py migrate`` to create the raster models

4. Add the TMS Endpoint to your urlconf::

        urlpatterns = patterns('',
            ...
            url(r'tiles/', include('raster.urls')),
        )

5. (Optional) Add ``RASTER_USE_CELERY = True`` to your project's setting to enable asynchronous raster parsing.

6. To add data, upload a raster file through the admin. Create a Legend object and call the tiles through the ``/tiles/myrasterfile.tif/{z}/{x}/{y}.png`` url setup previously.


Description
-----------
Django-raster provides basic integration of `raster data <http://en.wikipedia.org/wiki/GIS_file_formats#Raster>`_ into Django. It is based on the python bindings provided by the `GDAL <https://pypi.python.org/pypi/GDAL/>`_ package and PostGIS. Raster files can be uploaded and parsed through the admin interface. The raw raster data can be parsed asynchronously if `Celery <http://celeryproject.org/>`_ is integrated into the Django project (see below).

Once a raster file is uploaded, the parser will extract the data in the raster file and store the rasters in regular tiles of 256x256 pixels in a PostGIS raster table. Each tile will be one row in a PostGIS raster table.

For this, the package defines two models and one field:

* ``RasterLayer`` - storing the raw raster files and meta-data (for example rasterfile=raster.tif and srid=4326)

* ``RasterTile`` - storing the parsed raster in PostGis. The raster data is split into tiles of 256x256 pixels and each tile is stored as an instance of RasterTile. The raster data itself is stored in a *RasterField* within the RasterTile model.

* ``RasterField`` - an extension of the Django base Field class to store the raster data. The field converts PostGIS raster data from a database into Gdal Raster python objects and vice versa.

* ``OGRRaster`` - an object that stores raster data, in analogy to the OGRGeometry objects in GeoDjango.

Due to the simplicity of the implementation, currently no spatial querying can be done on the raster data through python. This package is not integrated with GeoDjango and has a very limited set of features when compared with GeoDjango spatial models (however, integration with GeoDjango is underway). If required, custom SQL can be used to make spatial queries on the raster data.

Usage
-----
After setting the package up, raster files can be uploaded through the admin interface using the RasterLayer model. Specify a layer name, the raster data type (continuous, categorical, mask or rank ordered), the raster's srid, the nodata value and the raster file to be uploaded.

Upon saving the a RasterLayer instance with a raster file, django-raster automatically loads the raster data from the file into a raster field in the RasterTile model. The RasterLayer instances have a *parse_log* field, which stores information about the parsing process. For debugging, there might be some useful information in the parse log.

A simple TMS view is part of this package as well, to serve the tiles with dynamic symbology. The endpoint is briefly described below, it works as a ``{z}/{x}/{y}.png`` url.

Asynchronous parsing with Celery
--------------------------------
For large rasters files the parsing step might take a while, so the html request that stored the raster might time out. To avoid this, django-raster can easily integrated with `Celery <http://celeryproject.org/>`_ .

To use celery for the raster parsing step, which is triggered automatically after saving RasterLayer instances, add the following setting to your django settings file::

        RASTER_USE_CELERY = True

If this setting is enabled, Celery pushes one task to the queue for each raster that is saved. The raster is then parsed upon execution of the task by a worker. The default of this setting is ``False``.

Pyramid building
----------------
Overview levels (or pyramids) are automatically created at the moment of importing the raster. The pyramid levels are aligned with the definition of a xyz style TMS service. Djago-raster will import the raster file in its original projection and flag those tiles with the ``is_base`` field. Subsequently a set of pyramids are created in the raster table. The pyramid is aligned with the XYZ tiles froma a tile map service, and will be accordingly indexed using the ``tilex``, ``tiley`` and ``tilez`` fields in the RasterTile table. The srid of the pyramid tiles is ``3857``.

Tile size
---------
The default tile size is 100x100 pixels. The tile size can be changed by providing an integer value in the ``RASTER_TILESIZE`` setting. The tiles are always saquares, so the tileize is set by one integer that specifies the number of pixels in each tile. For instance, setting::

        RASTER_TILESIZE = 100
        
will import the raster in tiles of 100x100 pixels.

Re-parsing data
---------------
Changing any of the fundamental settings such as the tile size will not automatically lead to an update for rasters that are already parsed. Only upon re-parsing of the rasters in the database, the data will be updated to the new values. When changing settings that change the raster tile structure, re-parse existing rasters to keep the database consistent. RasterLayers have a re-parse admin action to facilitate this.

RasterLayer methods
-------------------
The RasterLayer model will be extended such that it has spatial operations that can be performed at the rasterlayer level. It currently has a method to calculate counts for categorical layers. This function only works with categorical or mask raster layers. It returns a count in pixels for each distinct raster pixel value in the polygon provided to the function. If no polygon is provided, the counts are performed on the entire raster layer. For example::

         >>> mylayer = RasterLayer.objects.first()
         >>> mylayer.value_count('POLYGON ((30 10, 40 40, 20 40, 10 20, 30 10))')
         ... [{'count': 90679, 'value': 5.0},
              {'count': 4252237, 'value': 1.0},
              {'count': 4752665, 'value': 2.0},
              {'count': 685432, 'value': 3.0},
              {'count': 153598, 'value': 9.0}]

OGRRaster objects
-----------------
The RasterField uses OGRRaster objects to make raster data available through the field. The OGRRaster object stores the raster data in a gdal raster python object in the attribute ``ptr``. There are several methods that allow interacting with the data, such as the ``metadata`` property, that will return a dictionary with the raster header information.

Export raster as PIL Image
--------------------------
The OGRRaster objects that have discrete pixel values can be converted to a PIL image, through the img property. For each pixel value, an RGBA tuple can be specified in a dictionary colormap and passed to the img function. For example::

        >>> categories =  {
            1:  (225, 225, 225, 255),
            2:  (156, 156, 156, 255),
            3:  (255, 255, 190, 255),
            }
        >>> img = rast.img(categories)
        >>> img.size
        ... (200, 200)

TMS View
--------
Leveraging the img property of the rasters, a Tile Map Service (TMS) view is part of this package. The url can be included by::

        url(r'tiles/', include('raster.urls'))

The urlpattern will look for the filename of the raster to be shown, and xyz tiles in the RasterTiles table. A legend entry has to be created for the rasterlayer for any data to be shown. Any category that is not represented in the Legend will be invisible transparent pixels. An example request would be::

        /tile/myraster.tif/9/141/216.png

For use in javascript libraries such as leaflet or openlayers, the TMS enpoint for one rasterlayer can be included using::

        var layer = new L.tileLayer(/tiles/myraster.tif/{z}/{x}/{y}.png)

By default, the TMS view is cached for 24 hours, to change the timeout of the cache use the ``RASTER_TILE_CACHE_TIMEOUT`` setting. To disable caching, set this timeout to 0.

Legend Objects
--------------
To render XYZ tiles through the TMS view, a colormap or legend has to be created. A ``Legend`` object basically consists of a many-to-many field to ``LegendEntries``, which in turn define the expression used to filter pixels, a color and a foreign key to a ``LegendSemantics`` object. The LegendSemantics object defines the name, it is separated from the LegendEntry to be able to directly associate the semantics of pixel values from several different raster layers for analysis.

An example to create a Legend object with one LegendEntry is shown in the following snippet::

        >>> from raster.models import LegendSemantics, LegendEntry, Legend
        >>> semantics = LegendSemantics.objects.create(name='Earth')
        >>> entry = LegendEntry.objects.create(semantics=semantics, expression='1', color='#FFFFFF')
        >>> legend = Legend.objects.create(title='MyLegend')
        >>> legend.entries.add(entry)
        >>> legend.json
        ... '[{"color": "#FFFFFF", "expression": "1", "name": "Earth"}]'
