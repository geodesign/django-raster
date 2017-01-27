================
Raster Utilities
================
Django-raster hosts some utilities that ease the interaction with raster data.
The functions are located in ``raster.utils`` and ``raster.tiles.utils``.


.. function:: pixel_value_from_point(raster, point, band=0)

    Return the pixel value for the coordinate of the input point from selected
    band. 

    The input can be a point or tuple, if its a tuple it is assumed to be a
    pair of coordinates in the reference system of the raster. The band index
    to be used for extraction can be specified with the ``band`` keyword.

    Example::

        # Create a raster.
        >>> raster = GDALRaster({
            'width': 5,
            'height': 5,
            'srid': 4326,
            'bands': [{'data': range(25)}],
            'origin': (2, 2),
            'scale': (1, 1)
        })
        # Create a point at origin
        >>> point = OGRGeometry('SRID=4326;POINT(2 2)')
        # Get pixel value at origin.
        >>> pixel_value_from_point(raster, point)
        ... 0
        # Get pixel value from within the raster, using coordinate tuple input.
        >>> pixel_value_from_point(raster, (2, 3.5))
        ... 5
