import inspect
import os
import shutil
import tempfile

import numpy

from django.core.files import File
from django.core.urlresolvers import reverse
from django.test import Client, TransactionTestCase
from raster.models import Legend, LegendEntry, LegendSemantics, RasterLayer


class RasterTestCase(TransactionTestCase):

    def setUp(self):
        # Instantiate Django file instance for rasterlayer generation
        self.pwd = os.path.dirname(os.path.abspath(
            inspect.getfile(inspect.currentframe())
        ))

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
        ent7 = LegendEntry.objects.create(semantics=sem4, expression='(x >= 2) & (x < 5)', color='#123456')

        # Create legends
        leg = Legend.objects.create(title='MyLegend')
        leg.entries.add(ent1)

        self.legend = Legend.objects.create(title='Algebra Legend')
        self.legend.entries.add(ent2, ent3)

        leg2 = Legend.objects.create(title='Other')
        leg2.entries.add(ent4)

        leg3 = Legend.objects.create(title='Dual')
        leg3.entries.add(ent5, ent6)

        leg_expression = Legend.objects.create(title='Legend with Expression')
        leg_expression.entries.add(ent7)
        self.legend_with_expression = leg_expression

        # Create test raster layer
        rasterfile = File(open(os.path.join(self.pwd, 'raster.tif.zip'), 'rb'))
        self.media_root = tempfile.mkdtemp()
        with self.settings(MEDIA_ROOT=self.media_root):
            self.rasterlayer = RasterLayer.objects.create(
                name='Raster data',
                description='Small raster for testing',
                datatype='ca',
                nodata='255',
                rasterfile=rasterfile,
                legend=leg
            )
            # Create another layer with no tiles
            self.empty_rasterlayer = RasterLayer.objects.create(
                name='Raster data',
                description='Small raster for testing',
                datatype='ca',
                nodata='255',
                rasterfile=rasterfile
            )
            self.empty_rasterlayer.rastertile_set.all().delete()

        # Setup query urls for tests
        self.tile = self.rasterlayer.rastertile_set.get(tilez=11, tilex=552, tiley=858)
        self.tile_url = reverse('tms', kwargs={
            'z': self.tile.tilez, 'y': self.tile.tiley, 'x': self.tile.tilex,
            'layer': self.rasterlayer.id, 'format': '.png'
        })
        self.algebra_tile_url = reverse('algebra', kwargs={
            'z': self.tile.tilez, 'y': self.tile.tiley,
            'x': self.tile.tilex, 'format': '.png'
        })

        # Precompute expected totals from value count
        expected = {}
        for tile in self.rasterlayer.rastertile_set.filter(tilez=11):
            val, counts = numpy.unique(tile.rast.bands[0].data(), return_counts=True)
            for pair in zip(val, counts):
                if pair[0] in expected:
                    expected[pair[0]] += pair[1]
                else:
                    expected[pair[0]] = pair[1]

        # Drop nodata value (aggregation uses masked arrays)
        expected.pop(255)

        self.expected_totals = expected
        self.continuous_expected_histogram = {
            '(0.0, 1.5)': 22436,
            '(1.5, 3.0)': 56,
            '(13.5, 15.0)': 1244,
            '(3.0, 4.5)': 35621,
            '(7.5, 9.0)': 1350,
            '(9.0, 10.5)': 2977
        }

        # Instantiate test client
        self.client = Client()

    def tearDown(self):
        shutil.rmtree(self.media_root)
