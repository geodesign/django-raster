===========================
Django-raster documentation
===========================

**Currently under construction**

django-raster provides raster data integration for Django projects with a
PostGIS database backend. It is based on the Django internal raster data type
`RasterField`_ and gdal bindings through `GDALRaster`_.

Installation
------------

1. Install package with ``pip install django-raster``

2. Add "raster" to your INSTALLED_APPS setting like this::

    INSTALLED_APPS = (
        ...
        'raster',
    )

3. Run ``python manage.py migrate`` to create the raster models

4. Add the raster urls to your main urlconf::

    urlpatterns = patterns('',
        ...
        url(r'raster/', include('raster.urls')),
    )

5. (Optional) Add ``RASTER_USE_CELERY = True`` to your project's setting to
   enable asynchronous raster parsing.

Requirements
^^^^^^^^^^^^
Django-raster requires `Django >= 1.9`_ configured with the `PostGIS`__ backend,
as well as `GDAL`__.

.. _Django >= 1.9: https://docs.djangoproject.com/en/1.9/
__ http://postgis.net/
__ http://gdal.org/



Contents
--------

.. toctree::
    :maxdepth: 3

    introduction
    parser
    tms
    algebra
    settings
    ref/index

Indices and tables
------------------

* :ref:`genindex`
* :ref:`modindex`
