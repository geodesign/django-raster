from __future__ import unicode_literals

from django.contrib.gis.gdal import GDAL_VERSION, GDALRaster, OGRGeometry
from django.contrib.gis.geos import Point
from django.test import TestCase
from raster.rasterize import rasterize


class RasterizeGeometryTests(TestCase):

    def setUp(self):
        self.rast = GDALRaster({
            'datatype': 1,
            'driver': 'MEM',
            'width': 2,
            'height': 2,
            'nr_of_bands': 1,
            'srid': 3086,
            'origin': (500000, 400000),
            'scale': (100, -100),
            'skew': (0, 0),
            'bands': [{
                'nodata_value': 10,
                'data': range(4)
            }],
        })

    def test_covering_geom_rasterization(self):
        geom = OGRGeometry.from_bbox(self.rast.extent)
        geom.srid = 3086
        result = rasterize(geom, self.rast)

        self.assertEqual(result.bands[0].data().ravel().tolist(), [1, 1, 1, 1])
        self.assertEqual(result.geotransform, self.rast.geotransform)
        self.assertEqual(result.srs.wkt, self.rast.srs.wkt)

    def test_half_covering_geom_rasterization(self):
        geom = OGRGeometry.from_bbox((500000.0, 399800.0, 500200.0, 399900.0))
        geom.srid = 3086
        result = rasterize(geom, self.rast)
        self.assertEqual(result.bands[0].data().ravel().tolist(), [0, 0, 1, 1])

    def test_burn_value_option(self):
        geom = OGRGeometry.from_bbox((500000.0, 399800.0, 500200.0, 399900.0))
        geom.srid = 3086
        result = rasterize(geom, self.rast, burn_value=99)
        self.assertEqual(result.bands[0].data().ravel().tolist(), [0, 0, 99, 99])

    def test_rasterize_tiny_geom(self):
        geom = OGRGeometry.from_bbox((5e5, 4e5, 5e5 + 1e-3, 4e5 + 1e-3))
        geom.srid = 3086
        # Test default configuration for small geometries (not all touched).
        result = rasterize(geom, self.rast)
        self.assertEqual(result.bands[0].data().ravel().tolist(), [0, 0, 0, 0])
        # Switch the all touched option on.
        result = rasterize(geom, self.rast, all_touched=True)
        self.assertEqual(result.bands[0].data().ravel().tolist(), [1, 0, 0, 0])

    def test_rasterize_merge_algorithm_add(self):
        geom = OGRGeometry.from_bbox((500000.0, 399800.0, 500200.0, 399900.0))
        geom.srid = 3086
        result = rasterize(geom, self.rast)
        self.assertEqual(result.bands[0].data().ravel().tolist(), [0, 0, 1, 1])
        result = rasterize(geom, result, add=True)
        if GDAL_VERSION < (2, 1, 0):
            self.assertEqual(result.bands[0].data().ravel().tolist(), [0, 0, 1, 1])
        else:
            self.assertEqual(result.bands[0].data().ravel().tolist(), [0, 0, 2, 2])

    def test_rasterize_all_options_active(self):
        geom = Point(5e5 + 150, 4e5 - 150, srid=3086)
        # Test both options at the same time.
        result = rasterize(geom, self.rast, burn_value=99, all_touched=True, add=True)
        # Original raster is unchanged.
        self.assertEqual(self.rast.bands[0].data().ravel().tolist(), [0, 1, 2, 3])
        # Target raster is incremented.
        if GDAL_VERSION < (2, 1, 0):
            self.assertEqual(result.bands[0].data().ravel().tolist(), [0, 1, 2, 99])
        else:
            self.assertEqual(result.bands[0].data().ravel().tolist(), [0, 1, 2, 102])
