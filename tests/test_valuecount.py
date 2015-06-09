import inspect
import os
import shutil

import numpy

from django.contrib.gis.geos import Polygon
from django.core.files import File
from django.test import TestCase
from django.test.utils import override_settings
from raster.models import RasterLayer


@override_settings(RASTER_TILE_CACHE_TIMEOUT=0)
class RasterValueCountTests(TestCase):

    def setUp(self):
        # Instantiate Django file instances with nodes and links
        self.pwd = os.path.dirname(os.path.abspath(
            inspect.getfile(inspect.currentframe())))

        sourcefile = File(open(os.path.join(self.pwd, 'raster.tif.zip')))

        # Create raster layer
        self.rasterlayer = RasterLayer.objects.create(
            name='Raster data',
            description='Small raster for testing',
            datatype='ca',
            srid='3086',
            nodata='0',
            rasterfile=sourcefile)

        # Precompute expected totals from value count
        expected = {}
        for tile in self.rasterlayer.rastertile_set.filter(tilez=11):
            val, counts = numpy.unique(tile.rast.bands[0].data(), return_counts=True)
            for pair in zip(val, counts):
                if pair[0] in expected:
                    expected[pair[0]] += pair[1]
                else:
                    expected[pair[0]] = pair[1]

        self.expected_totals = expected

    def tearDown(self):
        shutil.rmtree(os.path.dirname(os.path.join(
            self.pwd, '..', self.rasterlayer.rasterfile.name)))
        self.rasterlayer.rastertile_set.all().delete()

    def test_value_count_no_geom(self):
        self.assertEqual(
            self.rasterlayer.value_count(),
            self.expected_totals
        )

    def test_value_count_with_geom_covering_all(self):
        # Set extent covering all tiles
        extent = (
            -10036039.001754418, 1028700.0747658457,
            -3016471.122513413, 5548267.9540068507
        )

        # Create polygon from extent
        bbox = Polygon.from_bbox(extent)
        bbox.srid = 3857

        # Confirm global count
        self.assertEqual(
            self.rasterlayer.value_count(bbox),
            self.expected_totals
        )

    def test_value_count_with_geom_covering_single_tile(self):
        # Get extent from single tile
        tile = self.rasterlayer.rastertile_set.get(tilez=11, tilex=552, tiley=858)
        extent = tile.rast.extent

        # Create polygon from extent
        bbox = Polygon.from_bbox(extent)
        bbox.srid = 3857

        expected = {}
        val, counts = numpy.unique(tile.rast.bands[0].data(), return_counts=True)
        for pair in zip(val, counts):
            if pair[0] in expected:
                expected[pair[0]] += pair[1]
            else:
                expected[pair[0]] = pair[1]

        # Confirm clipped count
        # The clip operation with the geom results in a small error when
        # compared to the exact count for a tile.
        self.assertEqual(
            self.rasterlayer.value_count(bbox),
            {
                0: expected[0] + 337,
                1: expected[1] + 1,
                2: expected[2],
                3: expected[3] + 12,
                4: expected[4] + 137,
                8: expected[8] + 2,
                9: expected[9] + 24
            }
        )
