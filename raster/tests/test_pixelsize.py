import inspect, os, shutil

from django.conf import settings
from django.test import TransactionTestCase
from django.test.utils import override_settings
from django.core.files import File

from raster.models import RasterLayer

class RasterLayerPixelsizeTests(TransactionTestCase):

    def setUp(self):
        # Instantiate Django file instances with nodes and links
        self.pwd = os.path.dirname(os.path.abspath(
            inspect.getfile(inspect.currentframe())))

        sourcefile = File(open(os.path.join(self.pwd, 'raster.tif')))

        # Create network with csv data attached
        self.rasterlayer = RasterLayer.objects.create(
            name='Raster data',
            description='Small raster for testing',
            datatype='ca',
            srid='3086',
            nodata='0',
            rasterfile=sourcefile)

        self.pixval = 113.307138294017

    def tearDown(self):
        shutil.rmtree(os.path.dirname(os.path.join(
            self.pwd, '../..', self.rasterlayer.rasterfile.name)))
        self.rasterlayer.rastertile_set.all().delete()

    def test_pixel_size_level1(self):
        result = self.rasterlayer.pixelsize(level=0)
        self.assertEqual((100,100), result)

    def test_pixel_size_level20(self):
        result = self.rasterlayer.pixelsize(level=20)
        result = (round(result[0], 3), round(result[1], 3))
        val = round(20*113.307138294017, 3)
        self.assertEqual((val, val), result)
