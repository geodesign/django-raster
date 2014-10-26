import os, tempfile, zipfile, shutil, datetime, struct, binascii, glob,\
    traceback
from math import pi
from osgeo import gdal, osr
from osgeo.gdalconst import GA_ReadOnly, GDT_Byte, GDT_Int16, GDT_UInt16, GDT_Int32,\
    GDT_UInt32, GDT_Float32, GDT_Float64

from django.db import connection
from django.conf import settings
from django.contrib.gis.geos import Polygon

from raster.models import RasterTile, RasterLayerMetadata

class RasterLayerParser:
    """Class to parse raster layers using gdal python bindings"""
    
    def __init__(self, rasterlayer):
        self.rasterlayer = rasterlayer

        self.rastername = os.path.basename(rasterlayer.rasterfile.name)

        self.gdalpixel2wktpixel = {
            GDT_Byte: 4, GDT_Int16: 5, GDT_UInt16: 6, GDT_Int32: 7,
            GDT_UInt32: 8, GDT_Float32: 10, GDT_Float64: 11
        }
        
        self.hextypes = {
            4: 'B', 5: 'h', 6: 'H', 7: 'i', 8: 'I', 10: 'f', 11: 'd'
        }
        
        self.tmpdir = ''

        # Set raster tilesize
        self.tilesize = int(getattr(settings, 'RASTER_TILESIZE', 256))

        # Turn padding on or off
        self.padding = getattr(settings, 'RASTER_PADDING', True)

        # Next up vs next down
        self.zoomdown = getattr(settings, 'RASTER_ZOOM_NEXT_HIGHER', True)

        # Set tile srid and basic tile geometry parameters
        self.global_srid = 3857
        self.worldsize = 2 * pi * 6378137
        self.tileshift = self.worldsize / 2.0

    def log(self, msg, reset=False):
        """Writes a message to the parse log of the rasterlayer instance"""
        # Prepare datetime stamp for log
        now = '[{0}] '.format(datetime.datetime.now().strftime('%Y-%m-%d %T'))
        
        # Write log, reset if requested
        if reset:
            self.rasterlayer.parse_log = now + msg
        else:
            self.rasterlayer.parse_log += '\n' + now + msg

        self.rasterlayer.save()

    def get_raster_file(self):
        """Make local copy of rasterfile (necessary if stored on CDN)"""

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
                self.log('WARNING: Found more than one file in zipfile '\
                         'using only first file found. This might lead '\
                         'to problems if its not a raster file.')

            # Return first one as raster file
            self.rastername = os.path.basename(raster_list[0])

    def open_raster_file(self):
        """Opens the raster file through gdal and extracts data values"""

        self.log('Opening raster file with gdal')

        # Open raster file
        self.dataset = gdal.Open(os.path.join(self.tmpdir, self.rastername), GA_ReadOnly)

        # Get data for first band
        self.band = self.dataset.GetRasterBand(1)
        self.geotransform = self.dataset.GetGeoTransform()

        # Store original metadata for this raster
        self.store_original_metadata()

        # Get raster meta info
        self.cols = self.dataset.RasterXSize
        self.rows = self.dataset.RasterYSize
        self.bands = self.dataset.RasterCount
        self.originX = self.geotransform[0]
        self.originY = self.geotransform[3]
        self.pixelWidth = self.geotransform[1]
        self.pixelHeight = self.geotransform[5]

    def reproject_raster(self, zoom):
        """
        Reprojects the gdal raster to the global srid setting.
        """
        self.log('Starting raster warp for zoom ' + str(zoom))

        # Get projections for source and destination
        srs = osr.SpatialReference()
        srs.ImportFromEPSG(self.global_srid)
        dest_wkt = srs.ExportToWkt()
        source_wkt = self.dataset.GetProjection()

        # Calculate warp geotransform
        bbox = self.rasterlayer.extent()
        indexrange = self.get_tile_index_range(bbox, zoom)
        bounds = self.get_tile_bounds(indexrange[0], indexrange[1], zoom)
        tilescalex, tilescaley = self.get_tile_scale(zoom)

        dest_geo = (bounds[0], tilescalex, 0.0, bounds[3], 0.0, tilescaley)

        # Create destination raster file
        sizex = (indexrange[2]-indexrange[0] + 1)*self.tilesize
        sizey = (indexrange[3]-indexrange[1] + 1)*self.tilesize
        dest_file = os.path.join(self.tmpdir, 'djangowarpedraster' + str(zoom) + '.tif')
        driver=gdal.GetDriverByName('GTiff')
        dest = driver.Create(dest_file, sizex, sizey, 1, self.band.DataType)
        dest.SetGeoTransform(dest_geo)
        dest.SetProjection(dest_wkt)

        # Warp image using nearest neighbor resampling
        gdal.ReprojectImage(
            self.dataset,
            dest,
            source_wkt,
            dest_wkt,
            gdal.GRA_NearestNeighbour
        )

        # Replace original dataset with warped version
        self.dataset = dest

        # Get data for first band
        self.band = self.dataset.GetRasterBand(1)
        self.geotransform = self.dataset.GetGeoTransform()

        # Get raster meta info
        self.cols = self.dataset.RasterXSize
        self.rows = self.dataset.RasterYSize
        self.bands = self.dataset.RasterCount
        self.originX = self.geotransform[0]
        self.originY = self.geotransform[3]
        self.pixelWidth = self.geotransform[1]
        self.pixelHeight = self.geotransform[5]

    def store_original_metadata(self):
        """
        Exports the input raster meta data to a RasterLayerMetadata object
        """
        lyrmeta = RasterLayerMetadata.objects.get_or_create(
            rasterlayer=self.rasterlayer)[0]
        lyrmeta.uperleftx=self.geotransform[0]
        lyrmeta.uperlefty=self.geotransform[3]
        lyrmeta.width=self.dataset.RasterXSize
        lyrmeta.height=self.dataset.RasterYSize
        lyrmeta.scalex=self.geotransform[1]
        lyrmeta.scaley=self.geotransform[5]
        lyrmeta.skewx=self.geotransform[2]
        lyrmeta.skewy=self.geotransform[4]
        lyrmeta.numbands=self.dataset.RasterCount
        lyrmeta.save()

    def get_raster_header(self, originx=None, originy=None,
                          sizex=None, sizey=None):
        """Gets the raster header in HEX format"""

        # Get data from objects if not set by user
        originx = originx or self.geotransform[0]
        originy = originy or self.geotransform[3]
        sizex = sizex or self.cols
        sizey = sizey or self.rows

        # Create header
        header = ''

        # Endiannes (little endian)
        header += self.bin2hex('B', 1)
        
        # Version
        header += self.bin2hex('H', 0)
        
        # Number of bands    
        header += self.bin2hex('H', 1)

        # Georeference
        header += self.bin2hex('d', self.geotransform[1]) # Scale x
        header += self.bin2hex('d', self.geotransform[5]) # Scale y
        header += self.bin2hex('d', originx)
        header += self.bin2hex('d', originy)
        header += self.bin2hex('d', self.geotransform[2]) # Skew x
        header += self.bin2hex('d', self.geotransform[4]) # Skew y        
        header += self.bin2hex('i', int(self.rasterlayer.srid)) # Set EPSG/SRID
        
        # Number of columns and rows
        header += self.bin2hex('H', sizex)
        header += self.bin2hex('H', sizey)

        return header

    def get_band_header(self):
        """Gets header for raster band"""
        header = ''

        # Recast pixel type
        pixtype = self.gdalpixel2wktpixel.get(self.band.DataType)

        # Set the pixeltype and HasNodata bit
        header += self.bin2hex('B', pixtype + 64)

        # Get nodata value, use user defined value if provided
        if self.rasterlayer.nodata:
            nodata = float(self.rasterlayer.nodata)
        else:
            nodata = self.band.GetNoDataValue()
        
        # Store hex version of nodata for raster tile padding
        self.nodata_hex = self.bin2hex(self.hextypes.get(pixtype), nodata)

        # Add encoded nodata value to band header
        header += self.nodata_hex

        return header

    def get_raster_content(self, startpixelx=0, startpixely=0,
                           sizex=None, sizey=None):
        """Extracts the pixel values from the raster in HEX format"""
        sizex = sizex or self.cols
        sizey = sizey or self.rows

        # Add column padding
        if self.padding and sizex < self.tilesize:
            # Get rows individually
            data = [self.band.ReadRaster(startpixelx, startpixely + i, sizex, 1) for i in range(0, sizey)]
            # Convert rows to hex
            data = [binascii.hexlify(dat).upper() for dat in data]
            # Add column padding to each row
            xpad = self.nodata_hex * (self.tilesize - sizex)
            data = [dat + xpad for dat in data]
            # Combine rows to block
            data = ''.join(data)
        else:
            data = self.band.ReadRaster(startpixelx, startpixely, sizex, sizey)
            data = binascii.hexlify(data).upper()

        # Add row padding
        if self.padding and sizey < self.tilesize:
            ypad = self.nodata_hex * self.tilesize
            data += ypad * (self.tilesize - sizey)

        # Check if raster is only null values
        if data == self.nodata_hex * self.tilesize * self.tilesize:
            return None
        else:
            return data

    def bin2hex(self, fmt, data):
        """Converts binary data to HEX, using little-endian byte order"""
        return binascii.hexlify(struct.pack('<' + fmt, data)).upper()

    def create_tiles(self, zoom=None):
        """
        Creates base tiles in original projection. These tiles are not intended
        for rendering but for analysis in the original projection. This makes
        value count statistics etc more accurate.
        """
        if zoom:
            self.log('Creating tiles for zoom ' + str(zoom))
        else:
            self.log('Creating tiles in original projection')

        for yblock in range(0, self.rows, self.tilesize):
            if yblock + self.tilesize < self.rows:
                numRows = self.tilesize
            else:
                numRows = self.rows - yblock

            for xblock in range(0, self.cols, self.tilesize):
                if xblock + self.tilesize < self.cols:
                    numCols = self.tilesize
                else:
                    numCols = self.cols - xblock
                
                # Calculate raster tile origin
                xorigin = self.originX + self.pixelWidth*xblock
                yorigin = self.originY + self.pixelHeight*yblock

                # Raster header
                if self.padding:
                    rasterheader = self.get_raster_header(xorigin, yorigin, self.tilesize, self.tilesize)
                else:
                    rasterheader = self.get_raster_header(xorigin, yorigin, numCols, numRows)

                # Raster band header
                bandheader = self.get_band_header()

                # Raster body content
                data = self.get_raster_content(xblock, yblock, numCols, numRows)
                if not data:
                    continue

                # Combine headers with data for inserting into postgis
                data = rasterheader + bandheader + data

                # Create tile
                tile = RasterTile(
                        rast=data,
                        rasterlayer=self.rasterlayer,
                        filename=self.rastername)

                # Set is_base flag or xyz tile indices
                if not zoom:
                    tile.is_base = True
                else:
                    bbox = self.rasterlayer.extent()
                    indexrange = self.get_tile_index_range(bbox, zoom)

                    tile.tilex = indexrange[0] + xblock/self.tilesize
                    tile.tiley = indexrange[1] + yblock/self.tilesize
                    tile.tilez = zoom

                # Save tile
                tile.save()

    def drop_empty_rasters(self):
        """
        Remove rasters that are only no-data from the current rasterlayer.
        """

        var = """
        DELETE FROM raster_rastertile
        WHERE ST_Count(rast)=0
        AND rasterlayer_id={0}
        """

        sql = var.format(self.rasterlayer.id)

        # Calculate tile in DB
        cursor=connection.cursor()
        cursor.execute(sql)

    def get_max_zoom(self, pixelsize):
        """
        Calculates the zoom level index z that is closest to the given scale.
        The input scale needs to be provided in meters per pixel. It is then
        compared to a list of pixel sizes for all TMS zoom levels.
        """
        # Calculate all pixelsizes for the TMS zoom levels
        tms_pixelsizes = [self.worldsize/(2.0**i*self.tilesize) for i in range(1,19)]

        # If the pixelsize is smaller than all tms sizes, default to max level
        zoomlevel = 18

        # Find zoomlevel (next-upper) for the input pixel size
        for i in range(0,18):
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
        zscale = self.worldsize / 2**z

        # Calculate overlaying tile indices
        return [
            int((bbox[0] + self.tileshift)/zscale),
            int((self.tileshift - bbox[3])/zscale),
            int((bbox[2] + self.tileshift)/zscale),
            int((self.tileshift - bbox[1])/zscale)
        ]

    def get_tile_bounds(self, x, y, z):
        """
        Calculates bounding box from Tile Map Service XYZ indices.
        """
        zscale = self.worldsize / 2**z

        xmin = x * zscale - self.tileshift
        xmax = (x+1) * zscale - self.tileshift
        ymin = self.tileshift - (y+1) * zscale
        ymax = self.tileshift - y * zscale

        return [xmin, ymin, xmax, ymax]

    def get_tile_scale(self, z):
        """Calculates pixel size scale for given zoom level"""

        zscale = self.worldsize / 2.0**z / self.tilesize
        return zscale, -zscale

    def parse_raster_layer(self):
        """
        This function pushes the raster data from the Raster Layer into the
        RasterTile table, in tiles of 100x100 pixels.
        """
        try:
            # Clean previous parse log
            self.log('Started parsing raster file', reset=True)

            # Download, unzip and open raster file
            self.get_raster_file()
            self.open_raster_file()

            # Remove existing tiles for this layer before loading new ones
            self.rasterlayer.rastertile_set.all().delete()

            # Create tiles in original projection and resolution
            self.create_tiles()
            self.drop_empty_rasters()

            # Setup TMS aligned tiles in world mercator
            scale = self.rasterlayer.rasterlayermetadata.scalex
            zoom = self.get_max_zoom(scale)

            # Loop through all lower zoom levels and create tiles
            for iz in range(zoom, -1, -1):
                self.reproject_raster(iz)
                self.create_tiles(iz)
            
            self.drop_empty_rasters()

            # Remove tempdir with raster files
            shutil.rmtree(self.tmpdir)

            # Log success of parsing
            self.log('Successfully finished parsing raster')

        except:
            shutil.rmtree(self.tmpdir)
            self.log(traceback.format_exc())
