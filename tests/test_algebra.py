from unittest import skipIf

from django.contrib.gis.gdal import GDALRaster
from django.test import TestCase
from django.test.utils import override_settings
from django.utils.encoding import iri_to_uri
from raster.formulas import RasterAlgebraParser

from .raster_testcase import RasterTestCase


class RasterAlgebraParserTests(TestCase):

    def setUp(self):
        base = {
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
            }],
        }

        base['bands'][0]['data'] = [10, 11, 12, 13]
        rast1 = GDALRaster(base)

        base['bands'][0]['data'] = [1, 1, 1, 1]
        rast2 = GDALRaster(base)

        base['bands'][0]['data'] = [30, 31, 32, 33]
        rast3 = GDALRaster(base)

        self.data = dict(zip(['x', 'y', 'z'], [rast1, rast2, rast3]))

    def test_algebra_parser(self):
        parser = RasterAlgebraParser()
        result = parser.evaluate_raster_algebra(self.data, 'x*(x>11) + 2*y + 3*z*(z==30)', check_aligned=True)
        self.assertEqual(result.bands[0].data().ravel().tolist(), [92, 2, 14, 15])


@override_settings(RASTER_TILE_CACHE_TIMEOUT=0)
class RasterAlgebraViewTests(RasterTestCase):

    def test_basic_algebra_request(self):
        response = self.client.get(self.algebra_tile_url + '?layers=a={0}&formula=a'.format(self.rasterlayer.id))
        self.assertEqual(response.status_code, 200)

    @skipIf(True, 'Not implemented yet, parser simply keeps first character from word.')
    def test_variable_name_lenghth_error(self):
        response = self.client.get(self.algebra_tile_url + '?layers=a={0}&formula=aa'.format(self.rasterlayer.id))
        self.assertEqual(response.status_code, 404)

    def test_undeclared_variable_name_error(self):
        response = self.client.get(self.algebra_tile_url + '?layers=a={0}&formula=a*b'.format(self.rasterlayer.id))
        self.assertEqual(response.status_code, 404)

    def test_valid_multi_formula_request(self):
        formula = iri_to_uri('a*(a<=5) + (a<5)')
        response = self.client.get(self.algebra_tile_url + '?layers=a={0}&formula={1}'.format(self.rasterlayer.id, formula))
        self.assertEqual(response.status_code, 200)

    def test_legend_id_specified(self):
        response = self.client.get(self.algebra_tile_url + '?layers=a={0}&formula=a&legend={1}'.format(self.rasterlayer.id, self.legend.id))
        self.assertEqual(response.status_code, 200)

    def test_legend_title_specified(self):
        response = self.client.get(self.algebra_tile_url + '?layers=a={0}&formula=a&legend={1}'.format(self.rasterlayer.id, self.legend.title))
        self.assertEqual(response.status_code, 200)

    def test_algebra_with_empty_tile(self):
        response = self.client.get(self.algebra_tile_url + '?layers=a={0},b={1}&formula=a*b&legend={2}'.format(self.rasterlayer.id, self.empty_rasterlayer.id, self.legend.title))
        self.assertEqual(response.status_code, 200)

    def test_nested_algebra_request(self):
        response = self.client.get(self.algebra_tile_url + '?layers=a={0},b={0}&formula=((a*5)%2B(b*3))*4'.format(self.rasterlayer.id))
        self.assertEqual(response.status_code, 200)
