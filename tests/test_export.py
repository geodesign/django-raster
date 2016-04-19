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

    def test_export_request(self):
        # Get export url
        url = reverse('export')
        # Request export for a simple algebra formula
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
