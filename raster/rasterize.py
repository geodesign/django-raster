from __future__ import unicode_literals

from ctypes import POINTER, c_char_p, c_double, c_int, c_void_p

import numpy

from django.contrib.gis.gdal import OGRGeometry
from django.contrib.gis.gdal.libgdal import std_call
from django.contrib.gis.gdal.prototypes.generation import voidptr_output

# Reference for GDALRasterizeGeometries
# http://gdal.org/gdal__alg_8h.html#a50caf4bc34703f0bcf515ecbe5061a0a

rasterize_geometries = voidptr_output(std_call('GDALRasterizeGeometries'),
    [c_void_p, c_int, POINTER(c_int), c_int, c_void_p, c_void_p, c_void_p, POINTER(c_double), POINTER(c_char_p), c_void_p, c_void_p],
    errcheck=False
)


def rasterize(geom, rast, burn_value=1, all_touched=False, add=False):
    """
    Rasterize a geometry. The result is aligned with the input raster.
    """
    # Create in memory target raster
    rasterized = rast.warp({'name': 'rasterized.MEM', 'driver': 'MEM'})

    # Set all values to zero if add option is off.
    if not add:
        rasterized.bands[0].data(numpy.zeros(rast.width * rast.height))

    # Set zero as nodata
    rasterized.bands[0].nodata_value = 0

    # Make sure geom is an OGR geometry
    if not isinstance(geom, OGRGeometry):
        geom = OGRGeometry(geom.ewkt)
    geom.transform(rast.srs)

    # Set rasterization parameters
    nr_of_bands_to_rasterize = 1
    band_indices_to_rasterize = (c_int * 1)(1)

    nr_of_geometries = 1
    burn_value = (c_double * 1)(burn_value)
    geometry_list = (c_void_p * 1)(geom.ptr)

    # Setup papsz options
    papsz_options = []
    if all_touched:
        papsz_options.append('ALL_TOUCHED=TRUE'.encode())
    if add:
        papsz_options.append('MERGE_ALG=ADD'.encode())

    papsz_options = (c_char_p * len(papsz_options))(*papsz_options)

    # Rasterize this geometry
    rasterize_geometries(
        rasterized.ptr,
        nr_of_bands_to_rasterize,
        band_indices_to_rasterize,
        nr_of_geometries,
        geometry_list,
        None, None,  # Transform parameters
        burn_value,
        papsz_options,
        None, None  # Progress functions
    )

    return rasterized
