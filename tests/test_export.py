import io
import os
import shutil
from tempfile import mkdtemp
from zipfile import ZipFile

import numpy

from django.contrib.gis.gdal import GDALRaster
from django.urls import reverse
from tests.raster_testcase import RasterTestCase


class RasterAlgebraViewTests(RasterTestCase):

    def tearDown(self):
        super(RasterAlgebraViewTests, self).tearDown()
        if hasattr(self, 'tmpdir'):
            shutil.rmtree(self.tmpdir)

    def get_export(self, bbox=None, colormap=None, description=None, name=None, zoom=None):
        # Setup the Get export url
        url = reverse('export')
        # Request export for a simple algebra formula
        url += '?layers=a={0}&formula=a'.format(self.rasterlayer.id)
        if bbox:
            url += '&bbox={0}'.format(bbox)
        if colormap:
            url += '&colormap={0}'.format(colormap)
        if description:
            url += '&description=' + description
        if name:
            url += '&filename=' + name
        if zoom:
            url += '&zoom={}'.format(zoom)
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
        response = self.get_export(description='Description%20with%20url%0Ahttp%3A//django-raster-example.org')
        self.unzip_response(response)
        readme = open(os.path.join(self.tmpdir, "README.txt"), "r").read()
        self.assertIn('Django Raster Algebra Export', readme)
        self.assertIn('Zoom level: 11', readme)
        self.assertIn('{0} "Raster data" (Formula label: a)'.format(self.rasterlayer.id), readme)
        self.assertIn('Tile index range x: 552 - 553', readme)
        self.assertIn('Tile index range y: 858 - 859', readme)
        self.assertIn('\na\n', readme)
        self.assertIn('Bounding-box: Minimum bounding-box covering all layers.', readme)
        self.assertIn(reverse('export'), readme)
        self.assertIn('Description with url\nhttp://django-raster-example.org', readme)

    def test_colormap(self):
        response = self.get_export(colormap='{"%281.134e-23%20%3C%3D%20x%29%20%26%20%28x%20%3C%205.234%29": [1,2,3,23], "5.234%20%3C%20x": "%23FFFFFF"}')
        self.unzip_response(response)
        colormap = open(os.path.join(self.tmpdir, "COLORMAP.txt"), "r").read()
        self.assertIn('1,2,3,23', colormap)
        self.assertIn('255,255,255,255', colormap)
        self.assertIn('5.234', colormap)

    def test_export_custom_name(self):
        response = self.get_export(name="model 23 (special edition 23.4)")
        self.unzip_response(response)
        expected_slug = 'algebra_export_model-23-special-edition-234'
        match = (expected_slug in name for name in os.listdir(self.tmpdir))
        self.assertTrue(any(match))

    def test_export_custom_zoom(self):
        response = self.get_export(zoom=3)
        self.unzip_response(response)
        readme = open(os.path.join(self.tmpdir, "README.txt"), "r").read()
        self.assertIn('Zoom level: 3', readme)
        self.assertIn('Tile index range x: 2 - 2', readme)
        self.assertIn('Tile index range y: 3 - 3', readme)
