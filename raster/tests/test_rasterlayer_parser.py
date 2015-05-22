import inspect
import os
import shutil

from django.core.files import File
from django.test import TestCase
from django.test.utils import override_settings
from raster.models import RasterLayer


@override_settings(RASTER_TILESIZE=100)
class RasterLayerParserWithoutCeleryTests(TestCase):

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
            rasterfile=sourcefile
        )

    def tearDown(self):
        shutil.rmtree(os.path.dirname(os.path.join(
            self.pwd, '../..', self.rasterlayer.rasterfile.name)))
        self.rasterlayer.rastertile_set.all().delete()

    def test_raster_layer_parsing(self):
        self.assertEqual(self.rasterlayer.rastertile_set.filter(is_base=True).count(), 4)
        self.assertEqual(self.rasterlayer.rastertile_set.filter(tilez=12).count(), 12)
        self.assertEqual(self.rasterlayer.rastertile_set.filter(tilez=11).count(), 4)
        self.assertEqual(self.rasterlayer.rastertile_set.filter(tilez=10).count(), 1)
        self.assertEqual(self.rasterlayer.rastertile_set.filter(tilez=9).count(), 1)
        self.assertEqual(self.rasterlayer.rastertile_set.filter(tilez=8).count(), 1)
        self.assertEqual(self.rasterlayer.rastertile_set.filter(tilez=7).count(), 1)
        self.assertEqual(self.rasterlayer.rastertile_set.filter(tilez=6).count(), 1)
        self.assertEqual(self.rasterlayer.rastertile_set.filter(tilez=5).count(), 1)
        self.assertEqual(self.rasterlayer.rastertile_set.filter(tilez=4).count(), 1)
        self.assertEqual(self.rasterlayer.rastertile_set.filter(tilez=3).count(), 1)
        self.assertEqual(self.rasterlayer.rastertile_set.filter(tilez=2).count(), 1)
        self.assertEqual(self.rasterlayer.rastertile_set.filter(tilez=1).count(), 1)
        self.assertEqual(self.rasterlayer.rastertile_set.filter(tilez=0).count(), 1)

    def test_raster_layer_parsing_after_file_change(self):
        self.rasterlayer.rastertile_set.all().delete()
        self.rasterlayer.rasterfile.name = 'raster_new.tif.zip'
        sourcefile = File(open(os.path.join(self.pwd, 'raster.tif.zip')),
                          'raster_new.tif.zip')
        self.rasterlayer.rasterfile = sourcefile
        self.rasterlayer.save()

        self.assertEqual(self.rasterlayer.rastertile_set.filter(is_base=True).count(), 4)
        self.assertEqual(self.rasterlayer.rastertile_set.filter(is_base=False).count(), 12 + 4 + 11)

    def test_layermeta_creation(self):
        self.assertEqual(self.rasterlayer.rasterlayermetadata.width, 163)


@override_settings(CELERY_ALWAYS_EAGER=True,
                   CELERY_EAGER_PROPAGATES_EXCEPTIONS=True,
                   RASTER_USE_CELERY=True,
                   RASTER_TILESIZE=100)
class RasterLayerParserWithCeleryTests(RasterLayerParserWithoutCeleryTests):
    pass
