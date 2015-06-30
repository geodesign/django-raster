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
from raster.const import WEB_MERCATOR_SRID, WEB_MERCATOR_TILESHIFT, WEB_MERCATOR_WORLDSIZE
from raster.models import RasterLayerMetadata, RasterTile


class RasterLayerParser:
    """
    Class to parse raster layers.
    """
    def __init__(self, rasterlayer):
        self.rasterlayer = rasterlayer

        self.rastername = os.path.basename(rasterlayer.rasterfile.name)

        # Set raster tilesize
        self.tilesize = int(getattr(settings, 'RASTER_TILESIZE', 256))
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
        Make local copy of rasterfile (necessary if files are stored on CDN).
        """
        self.log('Getting raster file from storage')

        self.tmpdir = tempfile.mkdtemp()

        # Access rasterfile and store locally
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
                self.log('WARNING: Found more than one file in zipfile '
                         'using only first file found. This might lead '
                         'to problems if its not a raster file.')

            # Return first one as raster file
            self.rastername = os.path.basename(raster_list[0])

    def open_raster_file(self):
        """
        Opens the raster file through gdal and extracts data values.
        """
        self.log('Opening raster file with gdal')

        # Open raster file
        self.dataset = GDALRaster(os.path.join(self.tmpdir, self.rastername), write=True)

        # Make sure nodata value is set from input
        for band in self.dataset.bands:
            band.nodata_value = float(self.rasterlayer.nodata)

        # Store original metadata for this raster
        self.store_original_metadata()

    def store_original_metadata(self):
        """
        Exports the input raster meta data to a RasterLayerMetadata object.
        """
        lyrmeta = RasterLayerMetadata.objects.get_or_create(
            rasterlayer=self.rasterlayer)[0]
        lyrmeta.uperleftx = self.dataset.origin.x
        lyrmeta.uperlefty = self.dataset.origin.y
        lyrmeta.width = self.dataset.width
        lyrmeta.height = self.dataset.height
        lyrmeta.scalex = self.dataset.scale.x
        lyrmeta.scaley = self.dataset.scale.y
        lyrmeta.skewx = self.dataset.skew.x
        lyrmeta.skewy = self.dataset.skew.y
        lyrmeta.numbands = len(self.dataset.bands)
        lyrmeta.save()

    def create_tiles(self, zoom):
        """
        Create tiles for this raster at the given zoomlevel.

        This routine first snaps the raster to the grid of the zoomlevel,
        then creates  the tiles from the snapped raster.
        """
        self.log('Starting raster warp for zoom ' + str(zoom))

        # Calculate warp geotransform
        bbox = self.rasterlayer.extent()
        indexrange = self.get_tile_index_range(bbox, zoom)
        bounds = self.get_tile_bounds(indexrange[0], indexrange[1], zoom)
        tilescalex, tilescaley = self.get_tile_scale(zoom)

        # Create destination raster file
        sizex = (indexrange[2] - indexrange[0] + 1) * self.tilesize
        sizey = (indexrange[3] - indexrange[1] + 1) * self.tilesize
        dest_file = os.path.join(self.tmpdir, 'djangowarpedraster' + str(zoom) + '.tif')

        snapped_dataset = self.dataset.warp({
            'origin': [bounds[0], bounds[3]],
            'scale': [tilescalex, tilescaley],
            'width': sizex,
            'height': sizey,
            'name': dest_file
        })

        self.log('Creating tiles for zoom ' + str(zoom))

        for yblock in range(0, snapped_dataset.height, self.tilesize):
            for xblock in range(0, snapped_dataset.width, self.tilesize):
                # Calculate raster tile origin
                xorigin = snapped_dataset.origin.x + snapped_dataset.scale.x * xblock
                yorigin = snapped_dataset.origin.y + snapped_dataset.scale.y * yblock
                # Create gdal in-memory raster
                dest = snapped_dataset.warp({
                    'driver': 'MEM', 'srid': WEB_MERCATOR_SRID,
                    'width': self.tilesize, 'height': self.tilesize,
                    'origin': [xorigin, yorigin],
                })

                # Create tile
                RasterTile.objects.create(
                    rast=dest,
                    rasterlayer=self.rasterlayer,
                    filename=self.rastername,
                    tilex=indexrange[0] + xblock / self.tilesize,
                    tiley=indexrange[1] + yblock / self.tilesize,
                    tilez=zoom
                )

        os.remove(dest_file)

    def drop_empty_rasters(self):
        """
        Remove rasters that are only no-data from the current rasterlayer.
        """
        # Setup SQL command
        sql = (
            "DELETE FROM raster_rastertile "
            "WHERE ST_Count(rast)=0 "
            "AND rasterlayer_id={0}"
        ).format(self.rasterlayer.id)

        # Run SQL to drop empty tiles
        cursor = connection.cursor()
        cursor.execute(sql)

    def get_max_zoom(self):
        """
        Calculates the zoom level index z that is closest to the given scale.
        The input scale needs to be provided in meters per pixel. It is then
        compared to a list of pixel sizes for all TMS zoom levels.
        """
        # Check if max zoom was manually specified
        if self.rasterlayer.max_zoom is not None:
            return self.rasterlayer.max_zoom

        # Get scale of raster
        pixelsize = self.dataset.scale.x

        # Calculate all pixelsizes for the TMS zoom levels
        tms_pixelsizes = [WEB_MERCATOR_WORLDSIZE / (2.0 ** i * self.tilesize) for i in range(1, 19)]

        # If the pixelsize is smaller than all tms sizes, default to max level
        zoomlevel = 18

        # Find zoomlevel (next-upper) for the input pixel size
        for i in range(0, 18):
            if pixelsize - tms_pixelsizes[i] >= 0:
                zoomlevel = i
                break

        # If nextdown setting is true, adjust level
        if self.zoomdown:
            zoomlevel += 1

        return zoomlevel

    def get_tile_index_range(self, bbox, z):
        """
        Calculates index range for a given bounding box and zoomlevel.
        It returns maximum and minimum x and y tile indices that overlap
        with the input bbox at zoomlevel z.
        """
        # Calculate tile size for given zoom level
        zscale = WEB_MERCATOR_WORLDSIZE / 2 ** z

        # Calculate overlaying tile indices
        return [
            int((bbox[0] + WEB_MERCATOR_TILESHIFT) / zscale),
            int((WEB_MERCATOR_TILESHIFT - bbox[3]) / zscale),
            int((bbox[2] + WEB_MERCATOR_TILESHIFT) / zscale),
            int((WEB_MERCATOR_TILESHIFT - bbox[1]) / zscale)
        ]

    def get_tile_bounds(self, x, y, z):
        """
        Calculates bounding box from Tile Map Service XYZ indices.
        """
        zscale = WEB_MERCATOR_WORLDSIZE / 2 ** z

        xmin = x * zscale - WEB_MERCATOR_TILESHIFT
        xmax = (x + 1) * zscale - WEB_MERCATOR_TILESHIFT
        ymin = WEB_MERCATOR_TILESHIFT - (y + 1) * zscale
        ymax = WEB_MERCATOR_TILESHIFT - y * zscale

        return [xmin, ymin, xmax, ymax]

    def get_tile_scale(self, z):
        """
        Calculates pixel size scale for given zoom level.
        """
        zscale = WEB_MERCATOR_WORLDSIZE / 2.0 ** z / self.tilesize
        return zscale, -zscale

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
            self.log('Transforming raster to SRID {0}'.format(WEB_MERCATOR_SRID))
            self.dataset = self.dataset.transform(WEB_MERCATOR_SRID)

            # Setup TMS aligned tiles in world mercator
            zoom = self.get_max_zoom()

            # Loop through all lower zoom levels and create tiles
            for iz in range(zoom + 1):
                self.create_tiles(iz)

            self.drop_empty_rasters()

            # Log success of parsing
            self.log('Successfully finished parsing raster')
        except:
            self.log(traceback.format_exc())
            raise
        finally:
            shutil.rmtree(self.tmpdir)
