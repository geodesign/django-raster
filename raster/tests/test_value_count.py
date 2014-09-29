import inspect, os, shutil

from django.conf import settings
from django.test import TransactionTestCase
from django.test.utils import override_settings
from django.core.files import File

from raster.models import RasterLayer

class RasterLayerValueCountTests(TransactionTestCase):

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

    def tearDown(self):
        shutil.rmtree(os.path.dirname(os.path.join(
            self.pwd, '../..', self.rasterlayer.rasterfile.name)))
        self.rasterlayer.rastertile_set.all().delete()

    def test_value_count_nogeom(self):
        results = self.rasterlayer.value_count()

        expected = {1:319, 2:26, 3:1885, 4:14320, 8:612, 9:1335}

        for res in results:
            self.assertEqual(res[1], expected[res[0]])      

    def test_value_count_full(self):
        results = self.rasterlayer\
            .value_count('SRID=3086;POLYGON((511700.468 417703.377,\
                          511700.468 435103.377,\
                          528000.468 435103.377,\
                          528000.468 417703.377,\
                          511700.468 417703.377))')

        expected = {1:319, 2:26, 3:1885, 4:14320, 8:612, 9:1335}

        for res in results:
            self.assertEqual(res[1], expected[res[0]])


    def test_value_count_miss(self):
        results = self.rasterlayer\
            .value_count('SRID=3086;POLYGON((528700 417703,\
                          528700 435103,\
                          529000 435103,\
                          529000 417703,\
                          528700 417703))')

        self.assertEqual(results, [])
