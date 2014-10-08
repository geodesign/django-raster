import inspect, os, shutil

from django.conf import settings
from django.test import TransactionTestCase
from django.test.utils import override_settings
from django.core.files import File

from raster.models import RasterLayer

class RasterLayerParserWithoutCeleryTests(TransactionTestCase):

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

    def test_raster_layer_parsing(self):
        self.assertEqual(self.rasterlayer.rastertile_set.filter(level=1).count(), 4)
        self.assertEqual(self.rasterlayer.rastertile_set.all().count(), 4+4+1+1+1+1+1)

    def test_raster_layer_parsing_after_file_change(self):
        self.rasterlayer.rastertile_set.all().delete()
        self.rasterlayer.rasterfile.name = 'raster_new.tif'
        sourcefile = File(open(os.path.join(self.pwd, 'raster.tif')),
                          'raster_new.tif')
        self.rasterlayer.rasterfile = sourcefile
        self.rasterlayer.save()
        self.assertEqual(self.rasterlayer.rastertile_set.filter(level=1).count(), 4)
        self.assertEqual(self.rasterlayer.rastertile_set.all().count(), 4+4+1+1+1+1+1)

    def test_layermeta_creation(self):
        self.assertEqual(self.rasterlayer.rasterlayermetadata.width, 163)

@override_settings(CELERY_ALWAYS_EAGER=True,
                   CELERY_EAGER_PROPAGATES_EXCEPTIONS=True,
                   RASTER_USE_CELERY=True)
class RasterLayerParserWithCeleryTests(RasterLayerParserWithoutCeleryTests):
    pass

@override_settings(RASTER_PADDING=False)
class RasterLayerParserNoPaddingTests(RasterLayerParserWithoutCeleryTests):
    pass

@override_settings(RASTER_TILESIZE=50)
class RasterLayerParserChangeTilesizeTests(RasterLayerParserWithoutCeleryTests):
    def test_raster_layer_parsing(self):
        self.assertEqual(self.rasterlayer.rastertile_set.filter(level=0).count(), 16)
        self.assertEqual(self.rasterlayer.rastertile_set.filter(level=1).count(), 16)
        self.assertEqual(self.rasterlayer.rastertile_set.filter(level=2).count(), 4)
        self.assertEqual(self.rasterlayer.rastertile_set.filter(level=4).count(), 1)
        self.assertEqual(self.rasterlayer.rastertile_set.filter(level=8).count(), 1)
        self.assertEqual(self.rasterlayer.rastertile_set.filter(level=16).count(), 1)
        self.assertEqual(self.rasterlayer.rastertile_set.filter(level=32).count(), 1)

    def test_raster_layer_parsing_after_file_change(self):
        self.rasterlayer.rastertile_set.all().delete()
        self.rasterlayer.rasterfile.name = 'raster_new.tif'
        sourcefile = File(open(os.path.join(self.pwd, 'raster.tif')),
                          'raster_new.tif')
        self.rasterlayer.rasterfile = sourcefile
        self.rasterlayer.save()
        self.assertEqual(self.rasterlayer.rastertile_set.filter(level=1).count(), 16)
        self.assertEqual(self.rasterlayer.rastertile_set.all().count(), 16+16+4+1+1+1+1)
