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
        self.assertEqual(
            self.rasterlayer.db_value_count(bbox),
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
        self.assertEqual(
            self.rasterlayer.value_count(bbox),
            expected
        )

        self.assertEqual(
            self.rasterlayer.db_value_count(bbox),
            expected
        )

    def test_area_calculation_with_geom_covering_single_tile(self):
        # Get extent from single tile
        tile = self.rasterlayer.rastertile_set.get(tilez=11, tilex=552, tiley=858)
        extent = tile.rast.extent

        # Create polygon from extent in default projection
        bbox = Polygon.from_bbox(extent)
        bbox.srid = WEB_MERCATOR_SRID
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
        area_per_pixel = 76.437028285175102837456506676971912384033 ** 2
        result = self.rasterlayer.value_count(bbox, area=True)
        for key, val in result.items():
            self.assertAlmostEqual(expected[key] * area_per_pixel, val, 5)
