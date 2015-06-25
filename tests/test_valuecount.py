import numpy

from django.contrib.gis.geos import Polygon
from django.test.utils import override_settings
from raster.const import WEB_MERCATOR_SRID

from .raster_testcase import RasterTestCase


@override_settings(RASTER_TILE_CACHE_TIMEOUT=0)
class RasterValueCountTests(RasterTestCase):

    def setUp(self):
        super(RasterValueCountTests, self).setUp()
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

    def test_value_count_no_geom(self):
        self.assertEqual(
            self.rasterlayer.value_count(),
            self.expected_totals
        )

    def test_value_count_with_geom_covering_all(self):
        # Set extent covering all tiles
        extent = (
            -10036039.001754418, 1028700.0747658457,
            -3016471.122513413, 5548267.9540068507,
        )

        # Create polygon from extent
        bbox = Polygon.from_bbox(extent)
        bbox.srid = WEB_MERCATOR_SRID

        # Confirm global count
        self.assertEqual(
            self.rasterlayer.value_count(bbox),
            self.expected_totals
        )

    def test_value_count_with_geom_covering_single_tile(self):
        # Get extent from single tile
        tile = self.rasterlayer.rastertile_set.get(tilez=11, tilex=552, tiley=858)
        extent = tile.rast.extent

        # Create polygon from extent, transform into different projection
        bbox = Polygon.from_bbox(extent)
        bbox.srid = WEB_MERCATOR_SRID
        bbox.transform(3086)

        # Compute expected counts for this tile
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
                0: expected[0] - 7,
                1: expected[1],
                2: expected[2],
                3: expected[3],
                4: expected[4] + 1,
                8: expected[8] + 1,
                9: expected[9] + 1,
            }
        )

    def test_area_calculation_with_geom_covering_single_tile(self):
        # Get extent from single tile
        tile = self.rasterlayer.rastertile_set.get(tilez=11, tilex=552, tiley=858)
        extent = tile.rast.extent

        # Create polygon from extent in default projection
        bbox = Polygon.from_bbox(extent)
        bbox.srid = WEB_MERCATOR_SRID

        # Confirm clipped count
        # The clip operation with the geom results in a small error when
        # compared to the exact count for a tile.
        self.assertEqual(
            self.rasterlayer.value_count(bbox, area=True),
            {
                0: 332182119.9074186,
                1: 712799.5537543764,
                2: 157750.7209128538,
                3: 6076324.064791405,
                4: 42878982.99183089,
                8: 940661.706184054,
                9: 2950522.7429996724,
            }
        )

        # Transform bbox to different coord system
        bbox.transform(3086)

        # Confirm clipped count
        # The clip operation with the geom results in a small error when
        # compared to the exact count for a tile.
        self.assertEqual(
            self.rasterlayer.value_count(bbox, area=True),
            {
                0: 256848447.15044078,
                1: 527185.5734562094,
                2: 122706.98692515219,
                3: 4676499.612814133,
                4: 32735497.289698936,
                8: 731697.218331463,
                9: 2181457.545336039,
            }
        )
