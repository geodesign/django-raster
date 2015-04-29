import inspect
import os
import shutil

from django.core.files import File
from django.test import TestCase
from raster.models import RasterLayer


class RasterLayerPixelsizeTests(TestCase):

    def setUp(self):
        # Instantiate Django file instances with nodes and links
        self.pwd = os.path.dirname(os.path.abspath(
            inspect.getfile(inspect.currentframe())))

        sourcefile = File(open(os.path.join(self.pwd, 'raster.tif.zip')))

        # Create network with csv data attached
        self.rasterlayer = RasterLayer.objects.create(
            name='Raster data',
            description='Small raster for testing',
            datatype='ca',
            srid='3086',
            nodata='0',
            rasterfile=sourcefile)

    def tearDown(self):
        shutil.rmtree(os.path.dirname(os.path.join(
            self.pwd, '../..', self.rasterlayer.rasterfile.name)))
        self.rasterlayer.rastertile_set.all().delete()

    def test_pixel_size_level1(self):
        result = self.rasterlayer.pixelsize()
        self.assertEqual((100, 100), result)
