from django.core.urlresolvers import reverse
from django.test.utils import override_settings

from .raster_testcase import RasterTestCase


@override_settings(RASTER_TILE_CACHE_TIMEOUT=0)
class RasterLegendViewTests(RasterTestCase):
    def test_tms_legend_url_from_layer_id(self):
        url = reverse('legend') + '?layer=' + str(self.rasterlayer.id)
        response = self.client.get(url)
        self.assertEqual(response.content, '[{"color": "#123456", "expression": "4", "name": "Earth"}]')
        self.assertEqual(response.status_code, 200)

    def test_tms_legend_url_error(self):
        url = reverse('legend', kwargs={'legend_id': '9999'})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_tms_legend_url_from_legend_id(self):
        url = reverse('legend', kwargs={'legend_id': self.legend.id})
        response = self.client.get(url)
        self.assertEqual(response.content, '[{"color": "#123456", "expression": "10", "name": "Earth"}, {"color": "#654321", "expression": "2", "name": "Wind"}]')
        self.assertEqual(response.status_code, 200)
