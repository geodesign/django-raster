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

        sourcefile = File(open(os.path.join(self.pwd, 'raster.tif.zip')))

        # Create network with csv data attached
        self.rasterlayer = RasterLayer.objects.create(
            name='Raster data',
            description='Small raster for testing',
            datatype='ca',
            srid='3086',
            nodata='0',
            rasterfile=sourcefile)

        self.wktgeom = 'POLYGON((400000 400000,\
                          400000 500000,\
                          600000 500000,\
                          600000 400000,\
                          400000 400000))'

        self.expected = {
            0: {"value": 0, "count": 47039},
            1: {"value": 1, "count": 319},
            2: {"value": 2, "count": 26},
            3: {"value": 3, "count": 1885},
            4: {"value": 4, "count": 14320},
            8: {"value": 8, "count": 612},
            9: {"value": 9, "count": 1335}
        }

    def tearDown(self):
        shutil.rmtree(os.path.dirname(os.path.join(
            self.pwd, '../..', self.rasterlayer.rasterfile.name)))
        self.rasterlayer.rastertile_set.all().delete()

    def test_value_count_nogeom(self):
        results = self.rasterlayer.value_count()

        for res in results:
            self.assertEqual(res, self.expected[res['value']])

    def test_value_count_full(self):
        results = self.rasterlayer\
            .value_count('SRID=3086;' + self.wktgeom)
        import ipdb; ipdb.set_trace()
        for res in results:
            self.assertEqual(res, self.expected[res['value']])

    def test_value_count_miss(self):
        results = self.rasterlayer\
            .value_count('SRID=3857;' + self.wktgeom)
        self.assertEqual(results, [])
