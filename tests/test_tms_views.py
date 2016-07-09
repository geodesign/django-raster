from __future__ import unicode_literals

from unittest import skip

from django.core.urlresolvers import reverse
from django.test.utils import override_settings
from raster.shortcuts import set_session_colormap
from tests.raster_testcase import RasterTestCase


@override_settings(RASTER_TILE_CACHE_TIMEOUT=0)
class RasterTmsTests(RasterTestCase):

    def test_tms_nonexisting_layer(self):
        url = reverse('tms', kwargs={
            'z': self.tile.tilez, 'y': self.tile.tiley, 'x': self.tile.tilex,
            'layer': 'raster_nonexistent.tif', 'format': '.png'
        })
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_tms_nonexisting_tile(self):
        url = reverse('tms', kwargs={'z': 100, 'y': 0, 'x': 0, 'layer': self.rasterlayer.id, 'format': '.png'})
        response = self.client.get(url)
        self.assertEqual(response['Content-type'], 'PNG')
        self.assertIsExpectedTile(response.content, 'test_tms_nonexisting_tile')
        self.assertEqual(response.status_code, 200)

    def test_tms_duplicated_layer_filename(self):
        url = reverse('tms', kwargs={'z': 100, 'y': 0, 'x': 0, 'layer': 'raster.tif', 'format': '.png'})
        DUPL_MSG = 'get() returned more than one RasterLayer -- it returned 2!'
        with self.assertRaisesMessage(Exception, DUPL_MSG):
            self.client.get(url)

    def test_tms_existing_tile(self):
        # Get tms tile rendered with legend
        response = self.client.get(self.tile_url)
        self.assertEqual(response['Content-type'], 'PNG')
        self.assertIsExpectedTile(response.content, 'test_tms_existing_tile')
        self.assertEqual(response.status_code, 200)

    @skip('Fails on current release -- Refs #25734.')
    def test_tms_existing_tile_without_legend(self):
        # Get tms tile for layer without legend
        self.rasterlayer.legend = None
        self.rasterlayer.save()
        response = self.client.get(self.tile_url)
        self.assertEqual(response['Content-type'], 'PNG')
        self.assertIsExpectedTile(response.content, 'test_tms_existing_tile_without_legend')
        self.assertEqual(response.status_code, 200)

    def test_tms_existing_tile_using_rasterlayer_id_in_url(self):
        url = reverse('tms', kwargs={
            'z': self.tile.tilez, 'y': self.tile.tiley, 'x': self.tile.tilex,
            'layer': self.rasterlayer.id, 'format': '.png'
        })

        # Get tms tile rendered with legend
        response = self.client.get(url)
        self.assertEqual(response['Content-type'], 'PNG')
        self.assertIsExpectedTile(response.content, 'test_tms_existing_tile_using_rasterlayer_id_in_url')
        self.assertEqual(response.status_code, 200)

    def test_tms_legend_query_arg(self):
        response = self.client.get(self.tile_url + '?legend=other')
        self.assertEqual(response['Content-type'], 'PNG')
        self.assertIsExpectedTile(response.content, 'test_tms_legend_query_arg')
        self.assertEqual(response.status_code, 200)

    def test_tms_manual_colormap_query_arg(self):
        response = self.client.get(self.tile_url + '?colormap={"4": [101, 67, 33, 255]}')
        self.assertEqual(response['Content-type'], 'PNG')
        self.assertIsExpectedTile(response.content, 'test_tms_manual_colormap_query_arg')
        self.assertEqual(response.status_code, 200)

    def test_tms_manual_colormap_query_arg_hex(self):
        response = self.client.get(self.tile_url + '?colormap={"4": "654321"}')
        self.assertEqual(response['Content-type'], 'PNG')
        self.assertIsExpectedTile(response.content, 'test_tms_manual_colormap_query_arg_hex')
        self.assertEqual(response.status_code, 200)

    def test_tms_entries_query_arg(self):
        response = self.client.get(self.tile_url + '?entries=4&legend=dual')
        self.assertEqual(response['Content-type'], 'PNG')
        self.assertIsExpectedTile(response.content, 'test_tms_entries_query_arg')
        self.assertEqual(response.status_code, 200)

    def test_tms_session_colormap(self):
        session = self.client.session
        set_session_colormap(session, 'SessionLegend', {
            "4": [255, 0, 255, 255],
        })
        session.save()
        response = self.client.get(self.tile_url + '?legend=SessionLegend&store=session')
        self.assertEqual(response['Content-type'], 'PNG')
        self.assertIsExpectedTile(response.content, 'test_tms_session_colormap')
        self.assertEqual(response.status_code, 200)

    def test_tms_session_colormap_overrides_database_legend(self):
        session = self.client.session
        set_session_colormap(session, 'MyLegend', {
            "4": [255, 0, 255, 255],
        })
        session.save()

        response = self.client.get(self.tile_url + '?legend=MyLegend&store=session')
        self.assertEqual(response['Content-type'], 'PNG')
        self.assertIsExpectedTile(response.content, 'test_tms_session_colormap_overrides_database_legend_store=session')
        self.assertEqual(response.status_code, 200)

        response = self.client.get(self.tile_url + '?legend=MyLegend')
        self.assertEqual(response['Content-type'], 'PNG')
        self.assertIsExpectedTile(response.content, 'test_tms_session_colormap_overrides_database_legend_store=database')
        self.assertEqual(response.status_code, 200)

    def test_tms_session_colormap_invalid_legend(self):
        response = self.client.get(self.tile_url + '?legend=MyLegend&store=session')
        self.assertEqual(response['Content-type'], 'PNG')
        self.assertIsExpectedTile(response.content, 'test_tms_session_colormap_invalid_legend')
        self.assertEqual(response.status_code, 200)
