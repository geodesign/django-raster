from __future__ import unicode_literals

import os
from unittest import skipIf

from django.core.files import File
from django.test import TestCase
from django.test.utils import override_settings
from raster.exceptions import RasterException
from raster.models import RasterLayer
from raster.tasks import parse
from tests.raster_testcase import RasterTestCase


@override_settings(RASTER_TILESIZE=100)
class RasterLayerParserTests(RasterTestCase):

    def test_raster_layer_parsing(self):
        self.assertEqual(self.rasterlayer.rastertile_set.filter(tilez=12).count(), 9)
        self.assertEqual(self.rasterlayer.rastertile_set.filter(tilez=11).count(), 4)
        self.assertEqual(self.rasterlayer.rastertile_set.filter(tilez=10).count(), 1)
        self.assertEqual(self.rasterlayer.rastertile_set.filter(tilez=9).count(), 1)
        self.assertEqual(self.rasterlayer.rastertile_set.filter(tilez=8).count(), 1)
        self.assertEqual(self.rasterlayer.rastertile_set.filter(tilez=7).count(), 1)
        self.assertEqual(self.rasterlayer.rastertile_set.filter(tilez=6).count(), 1)
        self.assertEqual(self.rasterlayer.rastertile_set.filter(tilez=5).count(), 1)
        self.assertEqual(self.rasterlayer.rastertile_set.filter(tilez=4).count(), 0)
        self.assertEqual(self.rasterlayer.rastertile_set.filter(tilez=3).count(), 0)
        self.assertEqual(self.rasterlayer.rastertile_set.filter(tilez=2).count(), 0)
        self.assertEqual(self.rasterlayer.rastertile_set.filter(tilez=1).count(), 0)
        self.assertEqual(self.rasterlayer.rastertile_set.filter(tilez=0).count(), 0)

    def test_raster_layer_parsing_after_file_change(self):
        self.rasterlayer.rastertile_set.all().delete()
        self.rasterlayer.rasterfile.name = 'raster_new.tif.zip'
        sourcefile = File(open(os.path.join(self.pwd, 'raster.tif.zip'), 'rb'),
                          'raster_new.tif.zip')
        self.rasterlayer.rasterfile = sourcefile
        with self.settings(MEDIA_ROOT=self.media_root):
            self.rasterlayer.save()

        self.assertEqual(self.rasterlayer.rastertile_set.count(), 9 + 4 + 6 * 1)

    def test_layermeta_creation(self):
        self.assertEqual(self.rasterlayer.metadata.width, 163)
        self.assertEqual(self.rasterlayer.metadata.max_zoom, 12)

    def test_reprojected_stored(self):
        self.assertIn('rasters/reprojected/', self.rasterlayer.reprojected.rasterfile.name)
        with self.settings(MEDIA_ROOT=self.media_root):
            self.rasterlayer.reprojected.delete()
            self.rasterlayer.store_reprojected = False
            self.rasterlayer.parsestatus.reset()
            self.rasterlayer.save()
            self.assertIsNone(self.rasterlayer.reprojected.rasterfile.name)

    def test_bandmeta_creation(self):
        self.assertEqual(self.rasterlayer.rasterlayerbandmetadata_set.count(), 1)
        meta = self.rasterlayer.rasterlayerbandmetadata_set.first()
        self.assertEqual(meta.min, 0)
        if meta.std is not None:
            self.assertAlmostEqual(meta.std, 2.4260526986669)

    def test_parsestatus_creation(self):
        self.assertEqual(self.rasterlayer.parsestatus.status, self.rasterlayer.parsestatus.FINISHED)
        self.assertEqual(self.rasterlayer.parsestatus.tile_levels, list(range(13)))

    def test_parse_nodata(self):
        self.assertEqual(self.tile.rast.bands[0].nodata_value, 255)
        self.assertIn('Setting no data values to 255.', self.rasterlayer.parsestatus.log)
        with self.settings(MEDIA_ROOT=self.media_root):
            self.rasterlayer.nodata = ''
            self.rasterlayer.parsestatus.reset()
            self.rasterlayer.save()
            tile = self.rasterlayer.rastertile_set.first()
            self.assertEqual(tile.rast.bands[0].nodata_value, 15)

    @skipIf(os.environ.get('CI', False), 'Assertion not raised on CI.')
    def test_parse_with_wrong_srid(self):
        with self.settings(MEDIA_ROOT=self.media_root):
            self.rasterlayer.srid = 4326
            msg = 'Failed to compute max zoom. Check the SRID of the raster.'
            with self.assertRaisesMessage(RasterException, msg):
                self.rasterlayer.save()

    def test_parse_with_source_url(self):
        with self.settings(MEDIA_ROOT=self.media_root):
            self.rasterlayer.rastertile_set.all().delete()
            self.rasterlayer.source_url = 'file://' + os.path.join(self.pwd, 'raster.tif.zip')
            self.rasterlayer.save()
            self.assertEqual(self.rasterlayer.rastertile_set.count(), 9 + 4 + 6 * 1)

    def test_parse_without_building_pyramid(self):
        with self.settings(MEDIA_ROOT=self.media_root):
            self.rasterlayer.rastertile_set.all().delete()
            self.rasterlayer.build_pyramid = False
            self.rasterlayer.save()
            self.assertEqual(self.rasterlayer.rastertile_set.filter(tilez=12).count(), 9)
            self.assertEqual(self.rasterlayer.rastertile_set.exclude(tilez=12).count(), 0)
            self.rasterlayer.max_zoom = 11
            self.rasterlayer.save()
            self.assertEqual(self.rasterlayer.rastertile_set.filter(tilez=11).count(), 4)
            self.assertEqual(self.rasterlayer.rastertile_set.exclude(tilez=11).count(), 0)


@override_settings(RASTER_TILESIZE=100, RASTER_USE_CELERY=False)
class RasterLayerParserWithoutCeleryTests(RasterTestCase):

    def test_raster_layer_parsing_without_celery(self):
        self.assertEqual(self.rasterlayer.rastertile_set.count(), 9 + 4 + 6 * 1)


class RasterParserWithoutDataTests(TestCase):

    def test_no_max_zoom(self):
        layer = RasterLayer.objects.create(name='No max zoom', build_pyramid=False)
        parse(layer)
        self.assertIn('Could not determine max zoom level, aborting prasing.', layer.parsestatus.log)
