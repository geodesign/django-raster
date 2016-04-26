from __future__ import unicode_literals

from django.contrib.gis.gdal import GDALRaster, OGRGeometry
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
