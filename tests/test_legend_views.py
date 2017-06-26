from __future__ import unicode_literals

import json

from django.core.urlresolvers import reverse

from .raster_testcase import RasterTestCase


class RasterLegendViewTests(RasterTestCase):
    def test_tms_legend_url_from_layer_id(self):
        url = reverse('legend') + '?layer=' + str(self.rasterlayer.id)
        response = self.client.get(url)
        self.assertEqual(
            json.loads(response.content.strip().decode()),
            [{"code": "1", "color": "#123456", "expression": "4", "name": "Earth"}],
        )
        self.assertEqual(response.status_code, 200)

    def test_tms_legend_url_error_wrong_legend_id(self):
        url = reverse('legend', kwargs={'legend_id': '9999'})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_tms_legend_url_error_wrong_raster_id(self):
        url = reverse('legend') + '?layer=9999'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_tms_legend_url_error_no_id(self):
        url = reverse('legend')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_tms_legend_url_from_legend_id(self):
        url = reverse('legend', kwargs={'legend_id': self.legend.id})
        response = self.client.get(url)
        self.assertEqual(
            json.loads(response.content.strip().decode()),
            [
                {"color": "#123456", "expression": "10", "code": "1", "name": "Earth"},
                {"color": "#654321", "expression": "2", "code": "2", "name": "Wind"},
            ]
        )
        self.assertEqual(response.status_code, 200)
