import inspect
import os
import shutil
import tempfile

from django.core.files import File
from django.core.urlresolvers import reverse
from django.test import Client, TestCase
from raster.models import Legend, LegendEntry, LegendSemantics, RasterLayer


class RasterTestCase(TestCase):

    def setUp(self):
        # Instantiate Django file instance for rasterlayer generation
        self.pwd = os.path.dirname(os.path.abspath(
            inspect.getfile(inspect.currentframe())
        ))
        rasterfile = File(open(os.path.join(self.pwd, 'raster.tif.zip')))
        # Create legend semantics
        sem1 = LegendSemantics.objects.create(name='Earth')
        sem2 = LegendSemantics.objects.create(name='Wind')
        sem3 = LegendSemantics.objects.create(name='Water')
        sem4 = LegendSemantics.objects.create(name='Fire')
        # Create legend entries (semantics with colors and expressions)
        ent1 = LegendEntry.objects.create(semantics=sem1, expression='4', color='#123456')
        ent2 = LegendEntry.objects.create(semantics=sem1, expression='10', color='#123456')
        ent3 = LegendEntry.objects.create(semantics=sem2, expression='2', color='#654321')
        ent4 = LegendEntry.objects.create(semantics=sem3, expression='4', color='#654321')
        ent5 = LegendEntry.objects.create(semantics=sem4, expression='4', color='#654321')
        ent6 = LegendEntry.objects.create(semantics=sem4, expression='5', color='#123456')
        # Create legends
        leg = Legend.objects.create(title='MyLegend')
        leg.entries.add(ent1)
        self.legend = Legend.objects.create(title='Algebra Legend')
        self.legend.entries.add(ent2, ent3)
        leg2 = Legend.objects.create(title='Other')
        leg2.entries.add(ent4)
        leg3 = Legend.objects.create(title='Dual')
        leg3.entries.add(ent5, ent6)
        # Create test raster layer
        self.media_root = tempfile.mkdtemp()
        with self.settings(MEDIA_ROOT=self.media_root):
            self.rasterlayer = RasterLayer.objects.create(
                name='Raster data',
                description='Small raster for testing',
                datatype='ca',
                srid='3086',
                nodata='0',
                rasterfile=rasterfile,
                legend=leg
            )
        # Create empty raster layer
        self.empty_rasterlayer = RasterLayer.objects.create(
            name='Raster data',
            description='Small raster for testing',
            datatype='ca',
            srid='3086',
            nodata='0',
        )
        # Setup query urls for tests
        self.tile = self.rasterlayer.rastertile_set.get(tilez=11, tilex=552, tiley=858)
        self.tile_url = reverse('tms', kwargs={'z': self.tile.tilez, 'y': self.tile.tiley, 'x': self.tile.tilex, 'layer': 'raster.tif', 'format': '.png'})
        self.algebra_tile_url = reverse('algebra', kwargs={'z': self.tile.tilez, 'y': self.tile.tiley, 'x': self.tile.tilex, 'format': '.png'})
        # Instantiate test client
        self.client = Client()

    def tearDown(self):
        shutil.rmtree(self.media_root)
