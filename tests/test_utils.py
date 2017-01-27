from __future__ import unicode_literals

import numpy

from django.contrib.gis.gdal import GDALRaster, OGRGeometry
from django.test import TestCase
from raster.exceptions import RasterException
from raster.tiles.utils import tile_bounds, tile_index_range
from raster.utils import colormap_to_rgba, hex_to_rgba, pixel_value_from_point, rescale_to_channel_range


class TestUtils(TestCase):

    def test_color_converter(self):
        # Check for conversion errors
        with self.assertRaises(RasterException):
            hex_to_rgba('')
        with self.assertRaises(RasterException):
            hex_to_rgba('#abcd')
        with self.assertRaises(RasterException):
            hex_to_rgba('#abcde')
        with self.assertRaises(RasterException):
            hex_to_rgba('#abcdefgh')

        self.assertEqual((0, 0, 0, 255), hex_to_rgba('#0'))
        self.assertEqual((0, 0, 0, 255), hex_to_rgba('#00'))
        self.assertEqual((0, 0, 0, 255), hex_to_rgba('#000'))
        self.assertEqual((0, 0, 0, 255), hex_to_rgba('#000000'))
        self.assertEqual((255, 255, 255, 100), hex_to_rgba('#FF', 100))
        self.assertEqual((171, 205, 239, 255), hex_to_rgba('abcdef'))

    def test_hex_colormap_to_rgba(self):
        colormap = {
            0: "#000000",
            1: "#00FF00",
            2: "#FF0000",
            3: "#0000FF"
        }
        converted_colormap = colormap_to_rgba(colormap)
        self.assertEqual(converted_colormap, {
            0: (0, 0, 0, 255),
            1: (0, 255, 0, 255),
            2: (255, 0, 0, 255),
            3: (0, 0, 255, 255)
        })

    def test_rgba_colormap_to_rgba(self):
        colormap = {
            0: (0, 0, 0, 0),
            1: (0, 255, 0, 255),
            2: (255, 0, 0, 255),
            3: (0, 0, 255, 255)
        }
        self.assertEqual(colormap, colormap_to_rgba(colormap))

    def test_empty_colormap_to_rgba(self):
        colormap = {}
        self.assertEqual(colormap, colormap_to_rgba(colormap))

    def test_tile_index_range(self):
        bounds = tile_bounds(43, 67, 8)
        geom = OGRGeometry.from_bbox(bounds)
        # With the default tolerance 0, the edging tiles are
        # included.
        idx = tile_index_range(geom.extent, 11)
        self.assertEqual(idx[2] - idx[0], 2 ** 3)
        self.assertEqual(idx[3] - idx[1], 2 ** 3)
        # With a larger tolerance, the strictly overlaping tiles are included.
        idx = tile_index_range(geom.extent, 11, tolerance=1e-3)
        self.assertEqual(idx[2] - idx[0], 2 ** 3 - 1)
        self.assertEqual(idx[3] - idx[1], 2 ** 3 - 1)

    def test_channel_rescale(self):
        data = numpy.array([0, 0.5, 1], dtype='float')
        numpy.testing.assert_equal(
            rescale_to_channel_range(data, 50, 40, None),
            [50, 45, 40]
        )
        numpy.testing.assert_equal(
            rescale_to_channel_range(data, 40, 50, None),
            [40, 45, 50]
        )
        numpy.testing.assert_equal(
            rescale_to_channel_range(data, 50, 50, None),
            [50, 50, 50]
        )
        numpy.testing.assert_equal(
            rescale_to_channel_range(data, 60, 50, 40),
            [60, 40, 50]
        )

    def test_get_pixel_value(self):
        raster = GDALRaster({'width': 5, 'height': 5, 'srid': 4326, 'bands': [{'data': range(25)}], 'origin': (2, 2), 'scale': (1, 1)})

        # Pixel value at origin.
        point = OGRGeometry('SRID=4326;POINT(2 2)')
        result = pixel_value_from_point(raster, point)
        self.assertEqual(result, 0)

        # Coords as tuple.
        result = pixel_value_from_point(raster, (2, 2))
        self.assertEqual(result, 0)

        # Point in different projection.
        point = OGRGeometry('SRID=3857;POINT(222638.9815865472 222684.20850554455)')
        result = pixel_value_from_point(raster, point)
        self.assertEqual(result, 0)

        # Pixel value outside of raster.
        point = OGRGeometry('SRID=4326;POINT(-2 2)')
        result = pixel_value_from_point(raster, point)
        self.assertEqual(result, None)

        point = OGRGeometry('SRID=4326;POINT(8 8)')
        result = pixel_value_from_point(raster, point)
        self.assertEqual(result, None)

        # Pixel values within the raster.
        point = OGRGeometry('SRID=4326;POINT(3.5 2)')
        result = pixel_value_from_point(raster, point)
        self.assertEqual(result, 1)

        point = OGRGeometry('SRID=4326;POINT(2 3.5)')
        result = pixel_value_from_point(raster, point)
        self.assertEqual(result, 5)

        point = OGRGeometry('SRID=4326;POINT(6.999 6.9999)')
        result = pixel_value_from_point(raster, point)
        self.assertEqual(result, 24)

        # Pixel value at "outer" edge of raster.
        point = OGRGeometry('SRID=4326;POINT(7 7)')
        result = pixel_value_from_point(raster, point)
        self.assertEqual(result, 24)

        # Point without srs specified.
        point = OGRGeometry('POINT(2 2)')
        with self.assertRaises(ValueError):
            pixel_value_from_point(raster, point)

        # Raster with negative scale on y axis.
        raster = GDALRaster({'width': 5, 'height': 5, 'srid': 4326, 'bands': [{'data': range(25)}], 'origin': (2, 2), 'scale': (1, -1)})
        point = OGRGeometry('SRID=4326;POINT(3 1)')
        result = pixel_value_from_point(raster, point)
        self.assertEqual(result, 6)
