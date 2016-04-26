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

    def test_simple_export_request(self, bbox=None):
        # Get export url
        url = reverse('export')
        # Request export for a simple algebra formula
        if bbox:
            response = self.client.get(url + '?layers=a={0}&formula=a&bbox={1}'.format(self.rasterlayer.id, bbox))
        else:
            response = self.client.get(url + '?layers=a={0}&formula=a'.format(self.rasterlayer.id))
        # Response status is OK
        self.assertEqual(response.status_code, 200)
        # Create tempdir, extract result into it
        tmpdir = mkdtemp()
        zf = ZipFile(io.BytesIO(b''.join(response.streaming_content)))
        zf.extractall(tmpdir)
        # Open result as GDALRaster
        rst = GDALRaster(os.path.join(tmpdir, zf.filelist[0].filename))
        # Size is 512x512
        self.assertEqual(rst.width, 512)
        self.assertEqual(rst.height, 512)
        # Compare upper left corner with raster layer tile
        numpy.testing.assert_equal(rst.bands[0].data(size=(256, 256)), self.tile.rast.bands[0].data())

    def test_bbox_export_request(self):
        # Request export for a simple algebra formula
        bbox = '-82.86445473318304,27.758967074520076,-82.69689154240895,27.917092083431676'
        self.test_simple_export_request(bbox)

    def test_export_request_too_large(self):
        # Get export url
        url = reverse('export')
        # Request export for a simple algebra formula
        response = self.client.get(url + '?layers=a={0}&formula=a&bbox=0,0,45,45'.format(self.rasterlayer.id))
        # Response status is OK
        self.assertEqual(response.status_code, 400)
