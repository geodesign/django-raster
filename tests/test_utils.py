from __future__ import unicode_literals

from django.contrib.gis.gdal import OGRGeometry
from django.test import TestCase
from raster.exceptions import RasterException
from raster.tiles.utils import tile_bounds, tile_index_range
from raster.utils import colormap_to_rgba, hex_to_rgba


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
