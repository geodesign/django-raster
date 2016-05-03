from __future__ import unicode_literals

import io
import os
from tempfile import mkdtemp
from zipfile import ZipFile

import numpy

from django.contrib.gis.gdal import GDALRaster
from django.core.urlresolvers import reverse
from django.test.utils import override_settings
from tests.raster_testcase import RasterTestCase


@override_settings(RASTER_TILE_CACHE_TIMEOUT=0)
class RasterAlgebraViewTests(RasterTestCase):

    def get_export(self, bbox=None, colormap=None):
        # Setup the Get export url
        url = reverse('export')
        # Request export for a simple algebra formula
        url += '?layers=a={0}&formula=a'.format(self.rasterlayer.id)
        if bbox:
            url += '&bbox={0}'.format(bbox)
        if colormap:
            url += '&colormap={0}'.format(colormap)
        # Request url and return response
        return self.client.get(url)

    def unzip_response(self, response):
        # Create tempdir, extract result into it
        self.tmpdir = mkdtemp()
        self.zf = ZipFile(io.BytesIO(b''.join(response.streaming_content)))
        self.zf.extractall(self.tmpdir)

    def check_exported_raster(self):
        # Open result as GDALRaster
        rst = GDALRaster(os.path.join(self.tmpdir, self.zf.filelist[0].filename))
        # Size is 512x512
        self.assertEqual(rst.width, 512)
        self.assertEqual(rst.height, 512)
        # Compare upper left corner with raster layer tile
        numpy.testing.assert_equal(
            rst.bands[0].data(size=(256, 256)),
            self.tile.rast.bands[0].data()
        )

    def test_simple_export_request(self):
        response = self.get_export()
        self.assertEqual(response.status_code, 200)
        self.unzip_response(response)
        self.check_exported_raster()

    def test_bbox_export_request(self):
        # Request export for a simple algebra formula
        bbox = '-82.86445473318304,27.758967074520076,-82.69689154240895,27.917092083431676'
        response = self.get_export(bbox=bbox)
        self.assertEqual(response.status_code, 200)
        self.unzip_response(response)
        self.check_exported_raster()

    def test_export_request_too_large(self):
        # Get export url
        response = self.get_export(bbox='0,0,45,45')
        # Request export for a simple algebra formula
        # Response status is OK
        self.assertEqual(response.status_code, 400)

    def test_readme_content(self):
        response = self.get_export()
        self.unzip_response(response)
        readme = open(os.path.join(self.tmpdir, "README.txt"), "r").read()
        self.assertIn('Django Raster Algebra Export', readme)
        self.assertIn('Zoom level: 11', readme)
        self.assertIn('Layer {0}: Raster data (Formula label: a)'.format(self.rasterlayer.id), readme)
        self.assertIn('Indexrange x: 552 - 553', readme)
        self.assertIn('Indexrange y: 858 - 859', readme)
        self.assertIn('Date:', readme)
        self.assertIn('Formula: a', readme)
        self.assertIn('BBox: No bbox provided, defaulted to maximum extent of input layers.', readme)
        self.assertIn('Url: ' + reverse('export'), readme)

    def test_colormap(self):
        response = self.get_export(colormap='{"%281.134e-23%20%3C%3D%20x%29%20%26%20%28x%20%3C%205.234%29": [1,2,3,0], "5.234%20%3C%20x": "%23FFFFFF"}')
        self.unzip_response(response)
        colormap = open(os.path.join(self.tmpdir, "COLORMAP.txt"), "r").read()
        self.assertIn('1,2,3,None', colormap)
        self.assertIn('255,255,255,None', colormap)
        self.assertIn('5.234', colormap)
