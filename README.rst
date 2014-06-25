==================
Rasters for Django
==================

Django app for simple raster data handling through the admin
interface, for Django projects using PostGIS database backends.

Detailed documentation will be in the "docs" directory.

Quick start
-----------

1. Add "raster" to your INSTALLED_APPS setting like this::

    INSTALLED_APPS = (
        ...
        'raster',
    )

2. Run `python manage.py migrate` to create the wms models.
