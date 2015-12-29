import datetime
import fnmatch
import os
import shutil
import tempfile
import traceback
import zipfile

import numpy

from django.conf import settings
from django.contrib.gis.gdal import GDALRaster
from django.core.files import File
from django.db import connection
from django.dispatch import Signal
from raster.models import RasterLayerBandMetadata, RasterLayerReprojected, RasterTile
from raster.tiles import utils
from raster.tiles.const import WEB_MERCATOR_SRID, WEB_MERCATOR_TILESIZE

rasterlayers_parser_ended = Signal(providing_args=['instance'])


class RasterLayerParser(object):
    """
    Class to parse raster layers.
    """
    def __init__(self, rasterlayer):
        self.rasterlayer = rasterlayer

        # Set raster tilesize
        self.tilesize = int(getattr(settings, 'RASTER_TILESIZE', WEB_MERCATOR_TILESIZE))
        self.zoomdown = getattr(settings, 'RASTER_ZOOM_NEXT_HIGHER', True)

        self.hist_values = []
        self.hist_bins = []

    def log(self, msg, reset=False, status=None, zoom=None):
        """
        Write a message to the parse log of the rasterlayer instance and update
        the parse status object.
        """
        if status is not None:
            self.rasterlayer.parsestatus.status = status

        if zoom is not None:
            self.rasterlayer.parsestatus.tile_level = zoom

        # Prepare datetime stamp for log
        now = '[{0}] '.format(datetime.datetime.now().strftime('%Y-%m-%d %T'))

        # Write log, reset if requested
        if reset:
            self.rasterlayer.parsestatus.log = now + msg
        else:
            self.rasterlayer.parsestatus.log += '\n' + now + msg

        self.rasterlayer.save()
        self.rasterlayer.parsestatus.save()

    def get_raster_file(self):
        """
        Make local copy of rasterfile, which is needed if files are stored on
        remote storage, and unzip it if necessary.
        """
        self.log('Getting raster file from storage')

        raster_workdir = getattr(settings, 'RASTER_WORKDIR', None)
        self.tmpdir = tempfile.mkdtemp(dir=raster_workdir)

        rprj, created = RasterLayerReprojected.objects.get_or_create(rasterlayer=self.rasterlayer)

        if not rprj.rasterfile:
            rasterfile_source = self.rasterlayer.rasterfile
        else:
            rasterfile_source = rprj.rasterfile

        self.rastername = os.path.basename(rasterfile_source.name)

        # Access rasterfile and store in a temp folder
        rasterfile = open(os.path.join(self.tmpdir, self.rastername), 'wb')
        for chunk in rasterfile_source.chunks():
            rasterfile.write(chunk)
        rasterfile.close()

        # If the raster file is compressed, decompress it
        file_name, file_extension = os.path.splitext(self.rastername)

        if file_extension == '.zip':
            # Open and extract zipfile
            zf = zipfile.ZipFile(os.path.join(self.tmpdir, self.rastername))
            zf.extractall(self.tmpdir)

            # Remove zipfile
            os.remove(os.path.join(self.tmpdir, self.rastername))

            # Get filelist from directory
            matches = []
            for root, dirnames, filenames in os.walk(self.tmpdir):
                for filename in fnmatch.filter(filenames, '*.*'):
                    matches.append(os.path.join(root, filename))

            # Check if only one file is found in zipfile
            if len(matches) > 1:
                self.log(
                    'WARNING: Found more than one file in zipfile '
                    'using only first file found. This might lead '
                    'to problems if its not a raster file.'
                )

            # Return first one as raster file
            self.rastername = os.path.basename(matches[0])

        # Open raster file
        self.dataset = GDALRaster(matches[0], write=True)

        # Extract metadata
        if created:
            self.extract_metadata()

        if not self.dataset.srs.srid == WEB_MERCATOR_SRID:
            self.log(
                'Transforming raster to SRID {0}'.format(WEB_MERCATOR_SRID),
                status=self.rasterlayer.parsestatus.REPROJECTING_RASTER
            )
            # Reproject the dataset
            self.dataset = self.dataset.transform(WEB_MERCATOR_SRID)

            # Zip reprojected raster file
            dest = tempfile.NamedTemporaryFile(dir=self.tmpdir, suffix='.zip')
            dest_zip = zipfile.ZipFile(dest.name, mode='w')
            dest_zip.write(self.dataset.name)
            dest_zip.close()

            # Store zip file in reprojected raster model
            rprj.rasterfile = File(open(dest_zip.filename, 'rb'))
            rprj.save()

    def extract_metadata(self):
        """
        Open the raster file as GDALRaster and set nodata-values.
        """
        self.log('Extracting metadata from raster.')

        # Make sure nodata value is set from input
        for i, band in enumerate(self.dataset.bands):
            if self.rasterlayer.nodata not in ('', None):
                band.nodata_value = float(self.rasterlayer.nodata)

            bandmeta = RasterLayerBandMetadata.objects.filter(rasterlayer=self.rasterlayer, band=i).first()
            if not bandmeta:
                bandmeta = RasterLayerBandMetadata(rasterlayer=self.rasterlayer, band=i)

            bandmeta.nodata_value = band.nodata_value
            bandmeta.min = band.min
            bandmeta.max = band.max
            bandmeta.save()

            # Prepare numpy hist values and bins
            self.hist_values.append(numpy.array(bandmeta.hist_values))
            self.hist_bins.append(numpy.array(bandmeta.hist_bins))

        # Store original metadata for this raster
        meta = self.rasterlayer.metadata

        meta.uperleftx = self.dataset.origin.x
        meta.uperlefty = self.dataset.origin.y
        meta.width = self.dataset.width
        meta.height = self.dataset.height
        meta.scalex = self.dataset.scale.x
        meta.scaley = self.dataset.scale.y
        meta.skewx = self.dataset.skew.x
        meta.skewy = self.dataset.skew.y
        meta.numbands = len(self.dataset.bands)
        meta.srs_wkt = self.dataset.srs.wkt
        meta.srid = self.dataset.srs.srid

        meta.save()

    def create_tiles(self, zoom):
        """
        Create tiles for this raster at the given zoomlevel.

        This routine first snaps the raster to the grid of the zoomlevel,
        then creates  the tiles from the snapped raster.
        """
        # Compute the tile x-y-z index range for the rasterlayer for this zoomlevel
        bbox = self.rasterlayer.extent()
        indexrange = utils.tile_index_range(bbox, zoom)
        quadrants = utils.quadrants(bbox, zoom)

        # Compute scale of tiles for this zoomlevel
        tilescale = utils.tile_scale(zoom)

        # Count the number of tiles that are required to cover the raster at this zoomlevel
        nr_of_tiles = (indexrange[2] - indexrange[0] + 1) * (indexrange[3] - indexrange[1] + 1)

        self.log('Creating {0} tiles in {1} quadrants at zoom {2}.'.format(nr_of_tiles, len(quadrants), zoom))

        for quadrant_index, indexrange in enumerate(quadrants):
            self.log('Starting tile creation for quadrant {0} at zoom level {1}'.format(quadrant_index, zoom))

            # Compute quadrant bounds and create destination file
            bounds = utils.tile_bounds(indexrange[0], indexrange[1], zoom)
            dest_file = tempfile.NamedTemporaryFile(dir=self.tmpdir, suffix='.tif')

            # Snap dataset to the quadrant
            snapped_dataset = self.dataset.warp({
                'name': dest_file.name,
                'origin': [bounds[0], bounds[3]],
                'scale': [tilescale, -tilescale],
                'width': (indexrange[2] - indexrange[0] + 1) * self.tilesize,
                'height': (indexrange[3] - indexrange[1] + 1) * self.tilesize,
            })

            # Create all tiles in this quadrant
            for tilex in range(indexrange[0], indexrange[2] + 1):
                for tiley in range(indexrange[1], indexrange[3] + 1):
                    # Calculate raster tile origin
                    bounds = utils.tile_bounds(tilex, tiley, zoom)

                    # Construct band data arrays
                    pixeloffset = (
                        (tilex - indexrange[0]) * self.tilesize,
                        (tiley - indexrange[1]) * self.tilesize
                    )

                    band_data = [
                        {
                            'data': band.data(offset=pixeloffset, size=(self.tilesize, self.tilesize)),
                            'nodata_value': band.nodata_value
                        } for band in snapped_dataset.bands
                    ]

                    # Add tile data to histogram
                    if zoom == self.max_zoom:
                        self.push_histogram(band_data)

                    # Warp source raster into this tile (in memory)
                    dest = GDALRaster({
                        'width': self.tilesize,
                        'height': self.tilesize,
                        'origin': [bounds[0], bounds[3]],
                        'scale': [tilescale, -tilescale],
                        'srid': WEB_MERCATOR_SRID,
                        'datatype': snapped_dataset.bands[0].datatype(),
                        'bands': band_data,
                    })

                    # Store tile
                    RasterTile.objects.create(
                        rast=dest,
                        rasterlayer=self.rasterlayer,
                        tilex=tilex,
                        tiley=tiley,
                        tilez=zoom
                    )

        # Store histogram data
        if zoom == self.max_zoom and len(self.hist_values):
            bandmetas = RasterLayerBandMetadata.objects.filter(rasterlayer=self.rasterlayer)
            for bandmeta in bandmetas:
                bandmeta.hist_values = self.hist_values[bandmeta.band].tolist()
                bandmeta.save()

        # Remove snapped dataset
        self.log('Finished zoom level {0}.'.format(zoom), zoom=zoom)

    def push_histogram(self, data):
        """
        Add data to band level histogram histogram.
        """
        if not len(self.hist_bins) or not len(self.hist_values):
            return

        # Loop through bands of this tile
        for i, dat in enumerate(data):
            # Create histogram for new data with the same bins
            new_hist = numpy.histogram(dat['data'], bins=self.hist_bins[i])
            # Add counts of this tile to band metadata histogram
            self.hist_values[i] += new_hist[0]

    def drop_empty_rasters(self):
        """
        Remove rasters that are only no-data from the current rasterlayer.
        """
        self.log(
            'Dropping empty raster tiles.',
            status=self.rasterlayer.parsestatus.DROPPING_EMPTY_TILES
        )

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
            self.log(
                'Started parsing raster file',
                reset=True,
                status=self.rasterlayer.parsestatus.DOWNLOADING_FILE
            )
            # Download, unzip and open raster file
            self.get_raster_file()

            # Remove existing tiles for this layer before loading new ones
            self.rasterlayer.rastertile_set.all().delete()

            # Compute max zoom at the web mercator projection
            self.max_zoom = utils.closest_zoomlevel(
                abs(self.dataset.scale.x)
            )

            # Store max zoom level in metadata
            self.rasterlayer.metadata.max_zoom = self.max_zoom
            self.rasterlayer.metadata.save()

            # Reduce max zoom by one if zoomdown flag was disabled
            if not self.zoomdown:
                self.max_zoom -= 1

            self.log(
                'Started creating tiles',
                status=self.rasterlayer.parsestatus.CREATING_TILES
            )

            # Loop through all lower zoom levels and create tiles to
            # setup TMS aligned tiles in world mercator
            for iz in range(self.max_zoom + 1):
                self.create_tiles(iz)

            self.drop_empty_rasters()

            # Send signal for end of parsing
            rasterlayers_parser_ended.send(sender=self.rasterlayer.__class__, instance=self.rasterlayer)

            # Log success of parsing
            self.log(
                'Successfully finished parsing raster',
                status=self.rasterlayer.parsestatus.FINISHED
            )
        except:
            self.log(
                traceback.format_exc(),
                status=self.rasterlayer.parsestatus.FAILED
            )
            raise
        finally:
            shutil.rmtree(self.tmpdir)
