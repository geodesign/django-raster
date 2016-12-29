import inspect
import os
import shutil
import tempfile
from importlib import import_module

import numpy

from django.conf import settings
from django.core.files import File
from django.test import Client, TransactionTestCase
from django.urls import reverse
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

        # Create legends
        leg = Legend.objects.create(title='MyLegend')
        self.legend = Legend.objects.create(title='Algebra Legend')
        leg2 = Legend.objects.create(title='Other')
        leg3 = Legend.objects.create(title='Dual')
        leg_expression = Legend.objects.create(title='Legend with Expression')
        self.legend_with_expression = leg_expression

        # Create legend entries (semantics with colors and expressions)
        LegendEntry.objects.create(legend=leg, semantics=sem1, expression='4', color='#123456', code='1')
        LegendEntry.objects.create(legend=self.legend, semantics=sem1, expression='10', color='#123456', code='1')
        LegendEntry.objects.create(legend=self.legend, semantics=sem2, expression='2', color='#654321', code='2')
        LegendEntry.objects.create(legend=leg2, semantics=sem3, expression='4', color='#654321', code='1')
        LegendEntry.objects.create(legend=leg3, semantics=sem4, expression='4', color='#654321', code='1')
        LegendEntry.objects.create(legend=leg3, semantics=sem4, expression='5', color='#123456', code='2')
        LegendEntry.objects.create(legend=leg_expression, semantics=sem4, expression='(x >= 2) & (x < 5)', color='#123456', code='1')

        # Create user session
        # https://docs.djangoproject.com/en/1.9/topics/http/sessions/#using-sessions-out-of-views
        engine = import_module(settings.SESSION_ENGINE)
        store = engine.SessionStore()
        store.save()
        self.client.cookies[settings.SESSION_COOKIE_NAME] = store.session_key

        # Create test raster layer
        rasterfile = File(
            open(os.path.join(self.pwd, 'raster.tif.zip'), 'rb'),
            name='raster.tif.zip'
        )
        settings.MEDIA_ROOT = tempfile.mkdtemp()
        self.media_root = settings.MEDIA_ROOT
        self.rasterlayer = RasterLayer.objects.create(
            name='Raster data',
            description='Small raster for testing',
            datatype='ca',
            rasterfile=rasterfile,
            legend=leg,
        )
        # Create another layer with no tiles
        self.empty_rasterlayer = RasterLayer.objects.create(
            name='Raster data',
            description='Small raster for testing',
            datatype='ca',
            rasterfile=rasterfile,
        )
        self.empty_rasterlayer.rastertile_set.all().delete()

        # Setup query urls for tests
        self.tile = self.rasterlayer.rastertile_set.get(tilez=11, tilex=552, tiley=858)
        self.tile_url = reverse('tms', kwargs={
            'z': self.tile.tilez, 'y': self.tile.tiley, 'x': self.tile.tilex,
            'layer': self.rasterlayer.id, 'frmt': 'png'
        })
        self.algebra_tile_url = reverse('algebra', kwargs={
            'z': self.tile.tilez, 'y': self.tile.tiley,
            'x': self.tile.tilex, 'frmt': 'png'
        })
        self.pixel_url = reverse('pixel', kwargs={
            'xcoord': -9218229,
            'ycoord': 3229269,
        })

        # Precompute expected totals from value count
        expected = {}
        for tile in self.rasterlayer.rastertile_set.filter(tilez=11):
            val, counts = numpy.unique(tile.rast.rast.bands[0].data(), return_counts=True)
            for pair in zip(val, counts):
                if pair[0] in expected:
                    expected[pair[0]] += pair[1]
                else:
                    expected[pair[0]] = pair[1]

        # Drop nodata value (aggregation uses masked arrays)
        expected.pop(255)

        self.expected_totals = expected
        self.continuous_expected_histogram = {
            '(0.0, 0.9)': 21741,
            '(0.9, 1.8)': 695,
            '(1.8, 2.7)': 56,
            '(2.7, 3.6)': 4131,
            '(3.6, 4.5)': 31490,
            '(4.5, 5.4)': 0,
            '(5.4, 6.3)': 0,
            '(6.3, 7.2)': 0,
            '(7.2, 8.1)': 1350,
            '(8.1, 9.0)': 2977
        }

        # Instantiate test client
        self.client = Client()

    def tearDown(self):
        shutil.rmtree(settings.MEDIA_ROOT)

    def assertIsExpectedTile(self, png, tile, frmt='png'):
        with open(os.path.join('tests/expected_tiles/', '{0}.{1}'.format(tile, frmt)), 'rb') as f:
            self.assertEqual(bytes(png), f.read())
