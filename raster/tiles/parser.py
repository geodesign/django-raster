from __future__ import unicode_literals

import datetime
import fnmatch
import os
import tempfile
import zipfile

import numpy
from celery import current_app, group
from celery.contrib.methods import task_method

from django.conf import settings
from django.contrib.gis.gdal import GDALRaster, OGRGeometry
from django.contrib.gis.gdal.error import GDALException
from django.core.files import File
from django.dispatch import Signal
from django.utils.six.moves.urllib.parse import urlparse
from django.utils.six.moves.urllib.request import urlretrieve
from raster.exceptions import RasterException
from raster.models import RasterLayer, RasterLayerBandMetadata, RasterLayerReprojected, RasterTile
from raster.tiles import utils
from raster.tiles.const import BATCH_STEP_SIZE, INTERMEDIATE_RASTER_FORMAT, WEB_MERCATOR_SRID, WEB_MERCATOR_TILESIZE

rasterlayers_parser_ended = Signal(providing_args=['instance'])


class RasterLayerParser(object):
    """
    Class to parse raster layers.
    """
    def __init__(self, rasterlayer_id):
        self.rasterlayer = RasterLayer.objects.get(id=rasterlayer_id)

        # Set raster tilesize
        self.tilesize = int(getattr(settings, 'RASTER_TILESIZE', WEB_MERCATOR_TILESIZE))

    def log(self, msg, status=None, zoom=None):
        """
        Write a message to the parse log of the rasterlayer instance and update
        the parse status object.
        """
        parsestatus = self.rasterlayer.parsestatus
        parsestatus.refresh_from_db()

        if status is not None:
            parsestatus.status = status

        if zoom is not None and zoom not in parsestatus.tile_levels:
            parsestatus.tile_levels.append(zoom)
            parsestatus.tile_levels.sort()

        # Prepare datetime stamp for log
        now = '[{0}] '.format(datetime.datetime.now().strftime('%Y-%m-%d %T'))

        if parsestatus.log:
            now = '\n' + now

        parsestatus.log += now + msg
        parsestatus.save()

    def open_raster_file(self):
        """
        Get raster source file to extract tiles from.

        This makes a local copy of rasterfile, unzips the raster and reprojects
        it into web mercator if necessary. The reprojected raster is stored for
        reuse such that reprojection does only happen once.

        The local copy of the raster is needed if files are stored on remote
        storages.
        """
        reproj, created = RasterLayerReprojected.objects.get_or_create(rasterlayer=self.rasterlayer)
        # Check if the raster has already been reprojected
        has_reprojected = reproj.rasterfile.name not in (None, '')

        # Create workdir
        raster_workdir = getattr(settings, 'RASTER_WORKDIR', None)
        self.tmpdir = tempfile.mkdtemp(dir=raster_workdir)

        # Choose source for raster data, use the reprojected version if it exists.
        if self.rasterlayer.source_url and not has_reprojected:
            url_path = urlparse(self.rasterlayer.source_url).path
            filename = url_path.split('/')[-1]
            filepath = os.path.join(self.tmpdir, filename)
            urlretrieve(self.rasterlayer.source_url, filepath)
        else:
            if has_reprojected:
                rasterfile_source = reproj.rasterfile
            else:
                rasterfile_source = self.rasterlayer.rasterfile

            if not rasterfile_source.name:
                raise RasterException('No data source found. Provide a rasterfile or a source url.')

            # Copy raster file source to local folder
            filepath = os.path.join(self.tmpdir, os.path.basename(rasterfile_source.name))
            rasterfile = open(filepath, 'wb')
            for chunk in rasterfile_source.chunks():
                rasterfile.write(chunk)
            rasterfile.close()

        # If the raster file is compressed, decompress it, otherwise try to
        # open the source file directly.
        if os.path.splitext(filepath)[1].lower() == '.zip':
            # Open and extract zipfile
            zf = zipfile.ZipFile(filepath)
            zf.extractall(self.tmpdir)

            # Remove zipfile
            os.remove(filepath)

            # Get filelist from directory
            matches = []
            for root, dirnames, filenames in os.walk(self.tmpdir):
                for filename in fnmatch.filter(filenames, '*.*'):
                    matches.append(os.path.join(root, filename))

            # Open the first raster file found in the matched files.
            self.dataset = None
            for match in matches:
                try:
                    self.dataset = GDALRaster(match)
                    break
                except GDALException:
                    pass

            # Raise exception if no file could be opened by gdal.
            if not self.dataset:
                raise RasterException('Could not open rasterfile.')
        else:
            self.dataset = GDALRaster(filepath)

        # Override srid if provided
        if self.rasterlayer.srid:
            try:
                self.dataset = GDALRaster(self.dataset.name, write=True)
            except GDALException:
                raise RasterException(
                    'Could not override srid because the driver for this '
                    'type of raster does not support write mode.'
                )
            self.dataset.srs = self.rasterlayer.srid

    def reproject_rasterfile(self):
        """
        Reproject the rasterfile into web mercator.
        """
        # Return if reprojected rasterfile already exists.
        if hasattr(self.rasterlayer, 'reprojected') and self.rasterlayer.reprojected.rasterfile.name:
            return

        # Return if the raster already has the right projection
        # and nodata value is acceptable.
        if self.dataset.srs.srid == WEB_MERCATOR_SRID:
            # SRID was not manually specified.
            if self.rasterlayer.nodata in ('', None):
                return
            # All bands from dataset already have the same nodata value as the
            # one that was manually specified.
            if all([self.rasterlayer.nodata == band.nodata_value
                    for band in self.dataset.bands]):
                return
        else:
            # Log projection change if original raster is not in web mercator.
            self.log(
                'Transforming raster to SRID {0}'.format(WEB_MERCATOR_SRID),
                status=self.rasterlayer.parsestatus.REPROJECTING_RASTER,
            )

        # Reproject the dataset.
        self.dataset = self.dataset.transform(
            WEB_MERCATOR_SRID,
            driver=INTERMEDIATE_RASTER_FORMAT,
        )

        # Manually override nodata value if neccessary
        if self.rasterlayer.nodata not in ('', None):
            self.log(
                'Setting no data values to {0}.'.format(self.rasterlayer.nodata),
                status=self.rasterlayer.parsestatus.REPROJECTING_RASTER,
            )
            for band in self.dataset.bands:
                band.nodata_value = float(self.rasterlayer.nodata)

        # Compress reprojected raster file and store it
        if self.rasterlayer.store_reprojected:
            dest = tempfile.NamedTemporaryFile(dir=self.tmpdir, suffix='.zip')
            dest_zip = zipfile.ZipFile(dest.name, 'w', allowZip64=True)
            dest_zip.write(
                filename=self.dataset.name,
                arcname=os.path.basename(self.dataset.name),
                compress_type=zipfile.ZIP_DEFLATED,
            )
            dest_zip.close()

            # Store zip file in reprojected raster model
            self.rasterlayer.reprojected.rasterfile = File(
                open(dest_zip.filename, 'rb'),
                name=os.path.basename(dest_zip.filename)
            )
            self.rasterlayer.reprojected.save()

        self.log('Finished transforming raster.')

    def create_initial_histogram_buckets(self):
        """
        Gets the empty histogram arrays for statistics collection.
        """
        self.hist_values = []
        self.hist_bins = []

        for i, band in enumerate(self.dataset.bands):
            bandmeta = RasterLayerBandMetadata.objects.filter(rasterlayer=self.rasterlayer, band=i).first()
            self.hist_values.append(numpy.array(bandmeta.hist_values))
            self.hist_bins.append(numpy.array(bandmeta.hist_bins))

    def extract_metadata(self):
        """
        Extract and store metadata for the raster and its bands.
        """
        self.log('Extracting metadata from raster.')

        # Try to compute max zoom
        try:
            max_zoom = self.compute_max_zoom()
        except GDALException:
            raise RasterException('Failed to compute max zoom. Check the SRID of the raster.')

        # Extract global raster metadata
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
        meta.max_zoom = max_zoom
        meta.save()

        # Extract band metadata
        for i, band in enumerate(self.dataset.bands):
            bandmeta = RasterLayerBandMetadata.objects.filter(rasterlayer=self.rasterlayer, band=i).first()
            if not bandmeta:
                bandmeta = RasterLayerBandMetadata(rasterlayer=self.rasterlayer, band=i)

            bandmeta.nodata_value = band.nodata_value
            bandmeta.min = band.min
            bandmeta.max = band.max
            # Depending on Django version, the band statistics include std and mean.
            if hasattr(band, 'std'):
                bandmeta.std = band.std
            if hasattr(band, 'mean'):
                bandmeta.mean = band.mean
            bandmeta.save()

        self.log('Finished extracting metadata from raster.')

    def create_tiles(self, zoom_levels):
        """
        Create tiles for input zoom levels, either a list or an integer.
        """
        if isinstance(zoom_levels, int):
            self.populate_tile_level(zoom_levels)
        else:
            for zoom in zoom_levels:
                self.populate_tile_level(zoom)

    def populate_tile_level(self, zoom):
        """
        Create tiles for this raster at the given zoomlevel.

        This routine first snaps the raster to the grid of the zoomlevel,
        then creates  the tiles from the snapped raster.
        """
        # Abort if zoom level is above resolution of the raster layer
        if zoom > self.max_zoom:
            return
        elif zoom == self.max_zoom:
            self.create_initial_histogram_buckets()

        # Compute the tile x-y-z index range for the rasterlayer for this zoomlevel
        bbox = self.dataset.extent
        quadrants = utils.quadrants(bbox, zoom)

        self.log('Creating {0} tiles in {1} quadrants at zoom {2}.'.format(self.nr_of_tiles(zoom), len(quadrants), zoom))

        # Process quadrants in parallell
        quadrant_task_group = group(self.process_quadrant.si(indexrange, zoom) for indexrange in quadrants)
        quadrant_task_group.apply()

        # Store histogram data
        if zoom == self.max_zoom:
            bandmetas = RasterLayerBandMetadata.objects.filter(rasterlayer=self.rasterlayer)
            for bandmeta in bandmetas:
                bandmeta.hist_values = self.hist_values[bandmeta.band].tolist()
                bandmeta.save()

        self.log('Finished parsing at zoom level {0}.'.format(zoom), zoom=zoom)

    _quadrant_count = 0

    @current_app.task(filter=task_method)
    def process_quadrant(self, indexrange, zoom):
        """
        Create raster tiles for a quadrant of tiles defined by a x-y-z index
        range and a zoom level.
        """
        self._quadrant_count += 1
        self.log(
            'Starting tile creation for quadrant {0} at zoom level {1}'.format(self._quadrant_count, zoom),
            status=self.rasterlayer.parsestatus.CREATING_TILES
        )

        # Compute scale of tiles for this zoomlevel
        tilescale = utils.tile_scale(zoom)

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

        # Create all tiles in this quadrant in batches
        batch = []
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

                # Ignore tile if its only nodata.
                if all([numpy.all(dat['data'] == dat['nodata_value']) for dat in band_data]):
                    continue

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

                # Store tile in batch array
                batch.append(
                    RasterTile(
                        rast=dest,
                        rasterlayer_id=self.rasterlayer.id,
                        tilex=tilex,
                        tiley=tiley,
                        tilez=zoom
                    )
                )

                # Commit batch to database and reset it
                if len(batch) == BATCH_STEP_SIZE:
                    RasterTile.objects.bulk_create(batch)
                    batch = []

        # Commit remaining objects
        if len(batch):
            RasterTile.objects.bulk_create(batch)

    def push_histogram(self, data):
        """
        Add data to band level histogram.
        """
        # Loop through bands of this tile
        for i, dat in enumerate(data):
            # Create histogram for new data with the same bins
            new_hist = numpy.histogram(dat['data'], bins=self.hist_bins[i])
            # Add counts of this tile to band metadata histogram
            self.hist_values[i] += new_hist[0]

    def drop_all_tiles(self):
        """
        Delete all existing tiles for this parser's rasterlayer.
        """
        self.log('Clearing all existing tiles.')
        self.rasterlayer.rastertile_set.all().delete()
        self.log('Finished clearing existing tiles.')

    def send_success_signal(self):
        """
        Send parser end signal for other dependencies to be handling new tiles.
        """
        self.log(
            'Successfully finished parsing raster',
            status=self.rasterlayer.parsestatus.FINISHED
        )
        rasterlayers_parser_ended.send(sender=self.rasterlayer.__class__, instance=self.rasterlayer)

    def compute_max_zoom(self):
        """
        Set max zoom property based on rasterlayer metadata.
        """
        # Return manual override value if provided
        if self.rasterlayer.max_zoom is not None:
            return self.rasterlayer.max_zoom

        if self.dataset.srs.srid == WEB_MERCATOR_SRID:
            # For rasters in web mercator, use the scale directly
            scale = abs(self.dataset.scale.x)
        else:
            # Create a line from the center of the raster to a point that is
            # one pixel width away from the center.
            xcenter = self.dataset.extent[0] + (self.dataset.extent[2] - self.dataset.extent[0]) / 2
            ycenter = self.dataset.extent[1] + (self.dataset.extent[3] - self.dataset.extent[1]) / 2
            linestring = 'LINESTRING({} {}, {} {})'.format(
                xcenter, ycenter, xcenter + self.dataset.scale.x, ycenter
            )
            line = OGRGeometry(linestring, srs=self.dataset.srs)

            # Tansform the line into web mercator.
            line.transform(WEB_MERCATOR_SRID)

            # Use the lenght of the transformed line as scale.
            scale = line.geos.length

        return utils.closest_zoomlevel(scale)

    @property
    def max_zoom(self):
        # Return manual override value if provided
        if self.rasterlayer.max_zoom is not None:
            return self.rasterlayer.max_zoom

        # Get max zoom from metadata
        if not hasattr(self.rasterlayer, 'metadata'):
            raise RasterException('Could not determine max zoom level.')
        max_zoom = self.rasterlayer.metadata.max_zoom

        # Reduce max zoom by one if zoomdown flag was disabled
        if not self.rasterlayer.next_higher:
            max_zoom -= 1

        return max_zoom

    def nr_of_tiles(self, zoom):
        """
        Compute the number of tiles for the rasterlayer on a given zoom level.
        """
        bbox = self.dataset.extent
        indexrange = utils.tile_index_range(bbox, zoom)
        return (indexrange[2] - indexrange[0] + 1) * (indexrange[3] - indexrange[1] + 1)
