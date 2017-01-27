from __future__ import unicode_literals

import numpy
from PIL import Image

from django.contrib.gis.gdal import OGRGeometry
from django.utils import six
from raster.algebra.parser import FormulaParser
from raster.exceptions import RasterException


def hex_to_rgba(value, alpha=255):
    """
    Converts a HEX color string to a RGBA 4-tuple.
    """
    value = value.lstrip('#')

    # Check length and input string property
    if len(value) not in [1, 2, 3, 6] or not value.isalnum():
        raise RasterException('Invalid color, could not convert hex to rgb.')

    # Repeat values for shortened input
    value = (value * 6)[:6]

    # Convert to rgb
    return int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16), alpha


def rescale_to_channel_range(data, dfrom, dto, dover=None):
    """
    Rescales an array to the color interval provided. Assumes that the data is normalized.

    This is used as a helper function for continuous colormaps.
    """
    # If the interval is zero dimensional, return constant array.
    if dfrom == dto:
        return numpy.ones(data.shape) * dfrom

    if dover is None:
        # Invert data going from smaller to larger if origin color is bigger
        # than target color.
        if dto < dfrom:
            data = 1 - data
        return data * abs(dto - dfrom) + min(dto, dfrom)
    else:
        # Divide data in upper and lower half.
        lower_half = data < 0.5
        # Recursive calls to scaling upper and lower half separately.
        data[lower_half] = rescale_to_channel_range(data[lower_half] * 2, dfrom, dover)
        data[numpy.logical_not(lower_half)] = rescale_to_channel_range((data[numpy.logical_not(lower_half)] - 0.5) * 2, dover, dto)

        return data


def band_data_to_image(band_data, colormap):
    """
    Creates an python image from pixel values of a GDALRaster.
    The input is a dictionary that maps pixel values to RGBA UInt8 colors.
    If an interpolation interval is given, the values are
    """
    # Get data as 1D array
    dat = band_data.ravel()
    stats = {}

    if 'continuous' in colormap:
        dmin, dmax = colormap.get('range', (dat.min(), dat.max()))

        if dmax == dmin:
            norm = dat == dmin
        else:
            norm = (dat - dmin) / (dmax - dmin)

        color_from = colormap.get('from', [0, 0, 0])
        color_to = colormap.get('to', [1, 1, 1])
        color_over = colormap.get('over', [None, None, None])

        red = rescale_to_channel_range(norm.copy(), color_from[0], color_to[0], color_over[0])
        green = rescale_to_channel_range(norm.copy(), color_from[1], color_to[1], color_over[1])
        blue = rescale_to_channel_range(norm.copy(), color_from[2], color_to[2], color_over[2])

        # Compute alpha channel from mask if available.
        if numpy.ma.is_masked(dat):
            alpha = 255 * numpy.logical_not(dat.mask) * (norm >= 0) * (norm <= 1)
        else:
            alpha = 255 * (norm > 0) * (norm < 1)

        rgba = numpy.array([red, green, blue, alpha], dtype='uint8').T
    else:
        # Create zeros array
        rgba = numpy.zeros((dat.shape[0], 4), dtype='uint8')

        # Replace matched rows with colors
        for key, color in colormap.items():
            orig_key = key
            try:
                # Try to use the key as number directly
                key = float(key)
                selector = dat == key
            except ValueError:
                # Otherwise use it as numpy expression directly
                parser = FormulaParser()
                selector = parser.evaluate({'x': dat}, key)

            # If masked, use mask to filter values additional to formula values
            if numpy.ma.is_masked(selector):
                selector.fill_value = False
                rgba[selector.filled() == 1] = color
                # Compress for getting statistics
                selector = selector.compressed()
            else:
                rgba[selector] = color

            # Track pixel statistics for this tile
            stats[orig_key] = int(numpy.sum(selector))

    # Reshape array to image size
    rgba = rgba.reshape(band_data.shape[0], band_data.shape[1], 4)

    # Create image from array
    img = Image.fromarray(rgba)

    return img, stats


def colormap_to_rgba(colormap):
    """
    Convert color ma to rgba colors.
    """
    if 'continuous' in colormap:
        return {k: hex_to_rgba(v) if isinstance(v, (six.string_types, int)) and k in ['from', 'to', 'over'] else v for k, v in colormap.items()}
    else:
        return {k: hex_to_rgba(v) if isinstance(v, (six.string_types, int)) else v for k, v in colormap.items()}


def pixel_value_from_point(raster, point, band=0):
    """
    Returns the pixel value for the coordinate of the input point from selected
    band.

    The input can be a point or tuple, if its a tuple it is assumed to be
    coordinates in the reference system of the raster.
    """
    if isinstance(point, (tuple, list)):
        point = OGRGeometry('POINT({0} {1})'.format(*point))
        point.srid = raster.srid
    elif not point.srs or not raster.srs:
        raise ValueError('Both the point and the raster are required to have a reference system specified.')
    elif point.srs != raster.srs:
        # Ensure the projection of the point is the same as of the raster.
        point.transform(raster.srid)

    # Return if point and raster do not touch.
    bbox = OGRGeometry.from_bbox(raster.extent)
    bbox.srs = raster.srs

    if not point.intersects(bbox):
        return

    # Compute position of point relative to raster origin.
    offset = (abs(raster.origin.x - point.coords[0]), abs(raster.origin.y - point.coords[1]))

    # Compute pixel index value based on offset.
    offset_index = [int(offset[0] / abs(raster.scale.x)), int(offset[1] / abs(raster.scale.y))]

    # If the point is exactly on the boundary, the offset_index is rounded to
    # a pixel index over the edge of the pixel. The index needs to be reduced
    # by one pixel for those cases.
    if offset_index[0] == raster.width:
        offset_index[0] -= 1

    if offset_index[1] == raster.height:
        offset_index[1] -= 1

    return raster.bands[band].data(offset=offset_index, size=(1, 1))[0, 0]
