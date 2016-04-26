from __future__ import unicode_literals

from django.test import TestCase
from raster.exceptions import RasterException
from raster.utils import hex_to_rgba


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
