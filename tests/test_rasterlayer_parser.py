import os
from shutil import copyfile

import mock

from django.contrib.gis.gdal import GDALRaster
from django.core.files import File
from django.test.utils import override_settings
from raster.exceptions import RasterException
from raster.models import RasterLayer
from raster.tasks import parse
from raster.tiles.const import WEB_MERCATOR_SRID
from tests.raster_testcase import RasterTestCase


def mock_download_file(*args, **kwargs):
    copyfile(kwargs['Key'], kwargs['Filename'])


@mock.patch('boto3.s3.inject.download_file', mock_download_file)
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
        lyr = RasterLayer.objects.get(id=self.rasterlayer.id)
        self.assertEqual(lyr.metadata.width, 163)
        self.assertEqual(lyr.metadata.max_zoom, 12)

    def test_reprojected_stored(self):
        lyr = RasterLayer.objects.get(id=self.rasterlayer.id)
        self.assertIn('rasters/reprojected/', lyr.reprojected.rasterfile.name)
        lyr.refresh_from_db()
        lyr.parsestatus.refresh_from_db()
        with self.settings(MEDIA_ROOT=self.media_root):
            lyr.reprojected.delete()
            lyr.store_reprojected = False
            lyr.parsestatus.reset()
            lyr.save()
            lyr = RasterLayer.objects.get(id=self.rasterlayer.id)
            self.assertEqual(lyr.reprojected.rasterfile.name, '')

    def test_bandmeta_creation(self):
        self.assertEqual(self.rasterlayer.rasterlayerbandmetadata_set.count(), 1)
        meta = self.rasterlayer.rasterlayerbandmetadata_set.first()
        self.assertEqual(meta.min, 0)
        if meta.std is not None:
            self.assertAlmostEqual(meta.std, 2.4260526986669)

    def test_parsestatus_creation(self):
        lyr = RasterLayer.objects.get(id=self.rasterlayer.id)
        self.assertEqual(lyr.parsestatus.status, self.rasterlayer.parsestatus.FINISHED)
        self.assertEqual(lyr.parsestatus.tile_levels, list(range(13)))

    def test_parse_nodata(self):
        with self.settings(MEDIA_ROOT=self.media_root):
            lyr = RasterLayer.objects.get(id=self.rasterlayer.id)
            lyr.nodata = 200
            lyr.save()
            tile = lyr.rastertile_set.first()
            self.assertEqual(tile.rast.bands[0].nodata_value, 200)

            lyr.parsestatus.refresh_from_db()
            self.assertIn('Setting no data values to 200.', lyr.parsestatus.log)

            lyr = RasterLayer.objects.get(id=self.rasterlayer.id)
            lyr.nodata = ''
            lyr.save()
            tile = lyr.rastertile_set.first()
            self.assertEqual(tile.rast.bands[0].nodata_value, 255)

    def test_parse_with_wrong_srid(self):
        with self.settings(MEDIA_ROOT=self.media_root):
            msg = 'Failed to compute max zoom. Check the SRID of the raster.'
            with self.assertRaisesMessage(RasterException, msg):
                self.rasterlayer.srid = 4326
                self.rasterlayer.save()

    def test_parse_with_source_url(self):
        with self.settings(MEDIA_ROOT=self.media_root):
            self.rasterlayer.rastertile_set.all().delete()
            self.rasterlayer.source_url = 'file://' + os.path.join(self.pwd, 'raster.tif.zip')
            self.rasterlayer.save()
            self.assertEqual(self.rasterlayer.rastertile_set.count(), 9 + 4 + 6 * 1)

    def test_parse_with_s3_source_url(self):
        self.rasterlayer.rastertile_set.all().delete()
        self.rasterlayer.source_url = 's3://rasterbucket/' + os.path.join(self.pwd, 'raster.tif.zip')
        self.rasterlayer.save()
        self.assertEqual(self.rasterlayer.rastertile_set.count(), 9 + 4 + 6 * 1)

    def test_parse_without_building_pyramid(self):
        lyr = RasterLayer.objects.get(id=self.rasterlayer.id)
        with self.settings(MEDIA_ROOT=self.media_root):
            lyr.rastertile_set.all().delete()
            lyr.metadata.delete()
            lyr.build_pyramid = False
            lyr.save()
            lyr = RasterLayer.objects.get(id=self.rasterlayer.id)
            self.assertEqual(lyr.rastertile_set.filter(tilez=12).count(), 9)
            self.assertEqual(lyr.rastertile_set.exclude(tilez=12).count(), 0)
            lyr.max_zoom = 11
            lyr.save()
            lyr = RasterLayer.objects.get(id=self.rasterlayer.id)
            self.assertEqual(lyr.rastertile_set.filter(tilez=11).count(), 4)
            self.assertEqual(lyr.rastertile_set.exclude(tilez=11).count(), 0)

    def test_no_rasterfile(self):
        layer = RasterLayer.objects.create(name='No max zoom', build_pyramid=False)
        msg = 'No data source found. Provide a rasterfile or a source url.'
        with self.assertRaisesMessage(RasterException, msg):
            parse(layer.id)

    def test_manual_nodata_override_matches_input_layer(self):
        with self.settings(MEDIA_ROOT=self.media_root):
            filepath = os.path.join(self.media_root, 'testraster.tif')
            GDALRaster({
                'name': filepath,
                'driver': 'tif',
                'width': 3,
                'height': 3,
                'origin': (-5e4, 5e4),
                'scale': [100, -100],
                'srid': WEB_MERCATOR_SRID,
                'bands': [
                    {'nodata_value': 0, 'data': range(9)},
                ],
            })
            rasterlayer = RasterLayer.objects.create(
                rasterfile=filepath,
                name='Raster data',
                nodata=0,
            )
            self.assertEqual(rasterlayer.rastertile_set.count(), 4)


@override_settings(RASTER_TILESIZE=100, RASTER_USE_CELERY=False)
class RasterLayerParserWithoutCeleryTests(RasterTestCase):

    def test_raster_layer_parsing_without_celery(self):
        self.assertEqual(self.rasterlayer.rastertile_set.count(), 9 + 4 + 6 * 1)


@override_settings(RASTER_TILESIZE=100, RASTER_PARSE_SINGLE_TASK=True)
class RasterLayerParserSingleTaskTests(RasterTestCase):

    def test_raster_layer_parsing_without_celery(self):
        self.assertEqual(self.rasterlayer.rastertile_set.count(), 9 + 4 + 6 * 1)
        self.rasterlayer.parsestatus.refresh_from_db()
        self.assertIn(
            'Parse task queued in all-in-one mode, waiting for worker availability.',
            self.rasterlayer.parsestatus.log,
        )
