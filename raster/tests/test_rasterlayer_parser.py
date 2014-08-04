import inspect, os

from django.test import TestCase
from django.test.utils import override_settings
from django.core.files import File

from ..models import RasterLayer

@override_settings(CELERY_ALWAYS_EAGER=True, CELERY_EAGER_PROPAGATES_EXCEPTIONS=True)
class RasterLayerParserTests(TestCase):

    def setUp(self):
        # Instantiate Django file instances with nodes and links
        self.pwd=os.path.dirname(os.path.abspath(
            inspect.getfile(inspect.currentframe())))
        sourcefile = File(open(os.path.join(self.pwd, 'raster.tif')),
            'raster.tif')
        
        # Create network with csv data attached
        self.rasterlayer = RasterLayer.objects.create(
            name='Raster data',
            description='Small raster for testing',
            datatype='ca',
            srid='3086',
            nodata='0',
            rasterfile=sourcefile)

    def tearDown(self):
        self.rasterlayer.delete()

    def test_raster_layer_parsing(self):
        # Make sure nodes and links have been created
        self.assertEqual(self.rasterlayer.rastertile_set.all().count(), 4)

    def test_raster_layer_parsing_after_file_change(self):
        self.rasterlayer.rastertile_set.all().delete()
        sourcefile = File(open(os.path.join(self.pwd, 'raster.tif')),
            'raster_new.tif')
        self.rasterlayer.sourcefile=sourcefile
        self.rasterlayer.save()
        self.assertEqual(self.rasterlayer.rastertile_set.all().count(), 4)
