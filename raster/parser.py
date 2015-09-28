import datetime
import glob
import os
import shutil
import tempfile
import traceback
import zipfile

from django.conf import settings
from django.contrib.gis.gdal import GDALRaster
from django.db import connection
from django.dispatch import Signal
from raster import tiler
from raster.const import WEB_MERCATOR_SRID, WEB_MERCATOR_TILESIZE
from raster.models import RasterLayerMetadata, RasterTile

rasterlayers_parser_ended = Signal(providing_args=['instance'])


class RasterLayerParser(object):
    """
    Class to parse raster layers.
    """
    def __init__(self, rasterlayer):
        self.rasterlayer = rasterlayer

        self.rastername = os.path.basename(rasterlayer.rasterfile.name)

        # Set raster tilesize
        self.tilesize = int(getattr(settings, 'RASTER_TILESIZE', WEB_MERCATOR_TILESIZE))
        self.zoomdown = getattr(settings, 'RASTER_ZOOM_NEXT_HIGHER', True)

    def log(self, msg, reset=False):
        """
        Write a message to the parse log of the rasterlayer instance.
        """
        # Prepare datetime stamp for log
        now = '[{0}] '.format(datetime.datetime.now().strftime('%Y-%m-%d %T'))

        # Write log, reset if requested
        if reset:
            self.rasterlayer.parse_log = now + msg
        else:
            self.rasterlayer.parse_log += '\n' + now + msg

        self.rasterlayer.save()

    def get_raster_file(self):
        """
        Make local copy of rasterfile, which is needed if files are stored on
        remote storage, and unzip it if necessary.
        """
        self.log('Getting raster file from storage')

        self.tmpdir = tempfile.mkdtemp()

        # Access rasterfile and store in a temp folder
        rasterfile = open(os.path.join(self.tmpdir, self.rastername), 'wb')
        for chunk in self.rasterlayer.rasterfile.chunks():
            rasterfile.write(chunk)
        rasterfile.close()

        # If the raster file is compress, decompress it
        fileName, fileExtension = os.path.splitext(self.rastername)

        if fileExtension == '.zip':

            # Open and extract zipfile
            zf = zipfile.ZipFile(os.path.join(self.tmpdir, self.rastername))
            zf.extractall(self.tmpdir)

            # Remove zipfile
            os.remove(os.path.join(self.tmpdir, self.rastername))

            # Get filelist from directory
            raster_list = glob.glob(os.path.join(self.tmpdir, "*.*"))

            # Check if only one file is found in zipfile
            if len(raster_list) > 1:
                self.log(
                    'WARNING: Found more than one file in zipfile '
                    'using only first file found. This might lead '
                    'to problems if its not a raster file.'
                )

            # Return first one as raster file
            self.rastername = os.path.basename(raster_list[0])

    def open_raster_file(self):
        """
        Open the raster file as GDALRaster and set nodata-values.
        """
        self.log('Opening raster file as GDALRaster.')

        # Open raster file
        self.dataset = GDALRaster(os.path.join(self.tmpdir, self.rastername), write=True)

        # Make sure nodata value is set from input
        if self.rasterlayer.nodata is not None:
            for band in self.dataset.bands:
                band.nodata_value = float(self.rasterlayer.nodata)

        # Store original metadata for this raster
        self.store_original_metadata()

    def store_original_metadata(self):
        """
        Exports the input raster meta data to a RasterLayerMetadata object.
        """
        lyrmeta = RasterLayerMetadata.objects.get_or_create(rasterlayer=self.rasterlayer)[0]
        lyrmeta.uperleftx = self.dataset.origin.x
        lyrmeta.uperlefty = self.dataset.origin.y
        lyrmeta.width = self.dataset.width
        lyrmeta.height = self.dataset.height
        lyrmeta.scalex = self.dataset.scale.x
        lyrmeta.scaley = self.dataset.scale.y
        lyrmeta.skewx = self.dataset.skew.x
        lyrmeta.skewy = self.dataset.skew.y
        lyrmeta.numbands = len(self.dataset.bands)
        lyrmeta.srs_wkt = self.dataset.srs.wkt
        lyrmeta.srid = self.dataset.srs.srid
        lyrmeta.max_zoom = tiler.closest_zoomlevel(
            abs(self.dataset.scale.x),
            self.zoomdown
        )

        lyrmeta.save()

    def create_tiles(self, zoom):
        """
        Create tiles for this raster at the given zoomlevel.

        This routine first snaps the raster to the grid of the zoomlevel,
        then creates  the tiles from the snapped raster.
        """
        # Compute the tile x-y-z index range for the rasterlayer for this zoomlevel
        bbox = self.rasterlayer.extent()
        indexrange = tiler.tile_index_range(bbox, zoom)

        # Compute scale of tiles for this zoomlevel
        tilescale = tiler.tile_scale(zoom)

        # Count the number of tiles that are required to cover the raster at this zoomlevel
        nr_of_tiles = (indexrange[2] - indexrange[0] + 1) * (indexrange[3] - indexrange[1] + 1)

        # Create destination raster file
        self.log('Snapping dataset to zoom level {0}'.format(zoom))

        bounds = tiler.tile_bounds(indexrange[0], indexrange[1], zoom)
        sizex = (indexrange[2] - indexrange[0] + 1) * self.tilesize
        sizey = (indexrange[3] - indexrange[1] + 1) * self.tilesize
        dest_file = os.path.join(self.tmpdir, 'djangowarpedraster' + str(zoom) + '.tif')

        snapped_dataset = self.dataset.warp({
            'name': dest_file,
            'origin': [bounds[0], bounds[3]],
            'scale': [tilescale, -tilescale],
            'width': sizex,
            'height': sizey,
        })

        self.log('Creating {0} tiles for zoom {1}.'.format(nr_of_tiles, zoom))

        counter = 0
        for tilex in range(indexrange[0], indexrange[2] + 1):
            for tiley in range(indexrange[1], indexrange[3] + 1):
                # Log progress
                counter += 1
                if counter % 250 == 0:
                    self.log('{0} tiles created at zoom {1}'.format(counter, zoom))

                # Calculate raster tile origin
                bounds = tiler.tile_bounds(tilex, tiley, zoom)

                # Warp source raster into this tile (in memory)
                dest = snapped_dataset.warp({
                    'driver': 'MEM',
                    'width': self.tilesize,
                    'height': self.tilesize,
                    'origin': [bounds[0], bounds[3]],
                })

                # Store tile
                RasterTile.objects.create(
                    rast=dest,
                    rasterlayer=self.rasterlayer,
                    filename=self.rastername,
                    tilex=tilex,
                    tiley=tiley,
                    tilez=zoom
                )

        # Remove snapped dataset
        self.log('Removing snapped dataset.')
        os.remove(dest_file)

    def drop_empty_rasters(self):
        """
        Remove rasters that are only no-data from the current rasterlayer.
        """
        self.log('Dropping empty raster tiles.')

        # Setup SQL command
        sql = (
            "DELETE FROM raster_rastertile "
            "WHERE ST_Count(rast)=0 "
            "AND rasterlayer_id={0}"
        ).format(self.rasterlayer.id)

        # Run SQL to drop empty tiles
        cursor = connection.cursor()
        cursor.execute(sql)

    def parse_raster_layer(self):
        """
        This function pushes the raster data from the Raster Layer into the
        RasterTile table.
        """
        try:
            # Clean previous parse log
            self.log('Started parsing raster file', reset=True)

            # Download, unzip and open raster file
            self.get_raster_file()
            self.open_raster_file()

            # Remove existing tiles for this layer before loading new ones
            self.rasterlayer.rastertile_set.all().delete()

            # Transform raster to global srid
            if self.dataset.srs.srid == WEB_MERCATOR_SRID:
                self.log('Dataset already in SRID {0}, skipping transform'.format(WEB_MERCATOR_SRID))
            else:
                self.log('Transforming raster to SRID {0}'.format(WEB_MERCATOR_SRID))
                self.dataset = self.dataset.transform(WEB_MERCATOR_SRID)

            # Loop through all lower zoom levels and create tiles to
            # setup TMS aligned tiles in world mercator
            for iz in range(self.rasterlayer.metadata.max_zoom + 1):
                self.create_tiles(iz)

            self.drop_empty_rasters()

            # Send signal for end of parsing
            rasterlayers_parser_ended.send(sender=self.rasterlayer.__class__, instance=self.rasterlayer)

            # Log success of parsing
            self.log('Successfully finished parsing raster')
        except:
            self.log(traceback.format_exc())
            raise
        finally:
            shutil.rmtree(self.tmpdir)
