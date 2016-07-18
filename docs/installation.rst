============
Installation
============
Django-raster requires ``Django >= 1.9`` configured with a `PostGIS`__ backend
and the `GDAL`__ library. The use of `Celery`_ is highly recommended (see
below).

__ https://docs.djangoproject.com/en/1.9/ref/contrib/gis/install/postgis/
__ https://docs.djangoproject.com/en/1.9/ref/contrib/gis/install/geolibs/#gdal

The package is available on PyPI, you can install it with::

    pip install django-raster

To integrate the package into Django, add ``raster`` to your
``INSTALLED_APPS`` setting like this::

    INSTALLED_APPS = (
        ...
        'raster',
    )

Django-raster has its own url structure (to serve raster data through a
``TMS`` endpoint for instance). To activate those urls, add the raster
urls to your main urlconf::

    urlpatterns = [
        ...
        url(r'^raster/', include('raster.urls')),
    ]

Finally, migrate your database to create the tables required by django-raster::

    python manage.py migrate


Distributed Task Management
----------------------------
Django-raster works best with `Celery`_, a distributed task queue manager.
Parsing raster files is a process that will time out most of the time if done
through regular http requests. If `Celery`_ is installed, several long running
tasks will be executed asynchronously in django-raster.

If you have `Celery`_ configured for your project, add the following
to your project's settings to tell django-raster to use it::

    RASTER_USE_CELERY = True

.. _Celery: http://celeryproject.org
