from django.test.utils import override_settings

from .raster_testcase import RasterTestCase


@override_settings(RASTER_TILE_CACHE_TIMEOUT=0)
class RasterAlgebraTests(RasterTestCase):

    def test_basic_algebra_request(self):
        response = self.client.get(self.algebra_tile_url + '?layers=a={0}&formula=y=a'.format(self.rasterlayer.id))
        self.assertEqual(response.status_code, 200)

    def test_variable_name_lenghth_error(self):
        response = self.client.get(self.algebra_tile_url + '?layers=a={0}&formula=y=aa'.format(self.rasterlayer.id))
        self.assertEqual(response.status_code, 404)

    def test_y_defined_twice_error(self):
        response = self.client.get(self.algebra_tile_url + '?layers=a={0}&formula=y=a,y=1'.format(self.rasterlayer.id))
        self.assertEqual(response.status_code, 404)

    def test_valid_multi_formula_request(self):
        response = self.client.get(self.algebra_tile_url + '?layers=a={0}&formula=y=a,a[a%3E5]=1'.format(self.rasterlayer.id))
        self.assertEqual(response.status_code, 200)

    def test_no_y_in_formulas_request(self):
        response = self.client.get(self.algebra_tile_url + '?layers=a={0}&formula=a=a,a[a%3E5]=1'.format(self.rasterlayer.id))
        self.assertEqual(response.status_code, 404)

    def test_legend_id_specified(self):
        response = self.client.get(self.algebra_tile_url + '?layers=a={0}&formula=y=a&legend={1}'.format(self.rasterlayer.id, self.legend.id))
        self.assertEqual(response.status_code, 200)

    def test_legend_title_specified(self):
        response = self.client.get(self.algebra_tile_url + '?layers=a={0}&formula=y=a&legend={1}'.format(self.rasterlayer.id, self.legend.title))
        self.assertEqual(response.status_code, 200)

    def test_algebra_with_empty_tile(self):
        response = self.client.get(self.algebra_tile_url + '?layers=a={0},b={1}&formula=y=a*b&legend={2}'.format(self.rasterlayer.id, self.empty_rasterlayer.id, self.legend.title))
        self.assertEqual(response.status_code, 200)
