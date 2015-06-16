import inspect
import os
import shutil

from django.core.files import File
from django.core.urlresolvers import reverse
from django.test import Client, TestCase
from django.test.utils import override_settings
from raster.models import Legend, LegendEntry, LegendSemantics, RasterLayer


@override_settings(RASTER_TILE_CACHE_TIMEOUT=0)
class RasterTmsTests(TestCase):

    def setUp(self):
        # Instantiate Django file instances with nodes and links
        self.pwd = os.path.dirname(os.path.abspath(
            inspect.getfile(inspect.currentframe())))

        sourcefile = File(open(os.path.join(self.pwd, 'raster.tif.zip')))

        self.legend = Legend.objects.create()

        # Create raster layer
        self.rasterlayer = RasterLayer.objects.create(
            name='Raster data',
            description='Small raster for testing',
            datatype='ca',
            srid='3086',
            nodata='0',
            rasterfile=sourcefile
        )

        self.tile = self.rasterlayer.rastertile_set.filter(is_base=False).first()
        self.tile_url = reverse('algebra', kwargs={'z': self.tile.tilez, 'y': self.tile.tiley, 'x': self.tile.tilex, 'format': '.png'})

        # Create raster layer and empty it
        self.empty_rasterlayer = RasterLayer.objects.create(
            name='Raster data',
            description='Small raster for testing',
            datatype='ca',
            srid='3086',
            nodata='0',
            rasterfile=sourcefile
        )
        self.empty_rasterlayer.rastertile_set.all().delete()

        # Create raster legend
        sem1 = LegendSemantics.objects.create(name='Earth')
        sem2 = LegendSemantics.objects.create(name='Wind')

        ent1 = LegendEntry.objects.create(semantics=sem1, expression='10', color='#123456')
        ent2 = LegendEntry.objects.create(semantics=sem2, expression='2', color='#654321')

        self.legend = Legend.objects.create(title='MyLegend')
        self.legend.entries.add(ent1, ent2)

        self.client = Client()

    def tearDown(self):
        shutil.rmtree(os.path.dirname(os.path.join(
            self.pwd, '..', self.rasterlayer.rasterfile.name)))
        self.rasterlayer.rastertile_set.all().delete()

    def test_basic_algebra_request(self):
        response = self.client.get(self.tile_url + '?layers=a={0}&formula=y=a'.format(self.rasterlayer.id))
        self.assertEqual(response.status_code, 200)

    def test_variable_name_lenghth_error(self):
        response = self.client.get(self.tile_url + '?layers=a={0}&formula=y=aa'.format(self.rasterlayer.id))
        self.assertEqual(response.status_code, 404)

    def test_y_defined_twice_error(self):
        response = self.client.get(self.tile_url + '?layers=a={0}&formula=y=a,y=1'.format(self.rasterlayer.id))
        self.assertEqual(response.status_code, 404)

    def test_valid_multi_formula_request(self):
        response = self.client.get(self.tile_url + '?layers=a={0}&formula=y=a,a[a%3E5]=1'.format(self.rasterlayer.id))
        self.assertEqual(response.status_code, 200)

    def test_no_y_in_formulas_request(self):
        response = self.client.get(self.tile_url + '?layers=a={0}&formula=a=a,a[a%3E5]=1'.format(self.rasterlayer.id))
        self.assertEqual(response.status_code, 404)

    def test_legend_id_specified(self):
        response = self.client.get(self.tile_url + '?layers=a={0}&formula=y=a&legend={1}'.format(self.rasterlayer.id, self.legend.id))
        self.assertEqual(response.status_code, 200)

    def test_legend_title_specified(self):
        response = self.client.get(self.tile_url + '?layers=a={0}&formula=y=a&legend={1}'.format(self.rasterlayer.id, self.legend.title))
        self.assertEqual(response.status_code, 200)

    def test_algebra_with_empty_tile(self):
        response = self.client.get(self.tile_url + '?layers=a={0},b={1}&formula=y=a*b&legend={2}'.format(self.rasterlayer.id, self.empty_rasterlayer.id, self.legend.title))
        self.assertEqual(response.status_code, 200)
