import os, tempfile, shutil, datetime, struct, binascii

from osgeo import gdal, osr
from osgeo.gdalconst import GA_ReadOnly, GDT_Byte, GDT_Int16, GDT_UInt16, GDT_Int32,\
    GDT_UInt32, GDT_Float32, GDT_Float64

from django.db import connection
from django.conf import settings

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
        if hasattr(settings, 'RASTER_TILESIZE'):
            self.tilesize = int(settings.RASTER_TILESIZE)
        else:
            self.tilesize = 100

        # Turn padding on or off
        if hasattr(settings, 'RASTER_PADDING'):
            self.padding = settings.RASTER_PADDING
        else:
            self.padding = True

        # Set overview levels for pyramid building
        if hasattr(settings, 'RASTER_OVERVIEW_LEVELS'):
            self.overview_levels = settings.RASTER_OVERVIEW_LEVELS
        else:
            self.overview_levels = [1, 2, 4, 8, 16, 32]

        # Set srid for pyramids
        if hasattr(settings, 'RASTER_GLOBAL_SRID'):
            self.global_srid = int(settings.RASTER_GLOBAL_SRID)
        else:
            self.global_srid = 3857

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
        """Make local copy of rasterfile (necessary if stored on CDS)"""
        
        self.tmpdir = tempfile.mkdtemp()

        # Access rasterfile and store locally
        try:
            rasterfile = open(os.path.join(self.tmpdir, self.rastername), 'wb')
            for chunk in self.rasterlayer.rasterfile.chunks():
                rasterfile.write(chunk)
            rasterfile.close()
            return True
        except IOError:
            shutil.rmtree(self.tmpdir)
            self.log('Error: Library error for download')
            return False

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

    def reproject_raster(self):
        """
        Reprojects the gdal raster to the global srid setting.
        """
        srs = osr.SpatialReference()
        srs.ImportFromEPSG(self.global_srid)
        dest_wkt = srs.ExportToWkt()
        source_wkt = self.dataset.GetProjection()
        self.dataset = gdal.AutoCreateWarpedVRT(self.dataset, 
                                                source_wkt,
                                                dest_wkt)
    
    def open_raster_file(self, reproject=False):
        """Opens the raster file through gdal and extracts data values"""
        # Open raster file
        self.dataset = gdal.Open(os.path.join(self.tmpdir, self.rastername), GA_ReadOnly)

        # Reproject to global srid if requested
        if reproject:
            self.reproject_raster()

        # Get data for first band
        self.band = self.dataset.GetRasterBand(1)
        self.geotransform = self.dataset.GetGeoTransform()

        # Store original metadata for this raster
        if not reproject:
            self.store_original_metadata()

        # Get raster meta info
        self.cols = self.dataset.RasterXSize
        self.rows = self.dataset.RasterYSize
        self.bands = self.dataset.RasterCount
        self.originX = self.geotransform[0]
        self.originY = self.geotransform[3]
        self.pixelWidth = self.geotransform[1]
        self.pixelHeight = self.geotransform[5]

    def get_raster_header(self, originx=None, originy=None,
                          sizex=None, sizey=None, srid=None):
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
        header += self.bin2hex('i', srid) # Set EPSG/SRID
        
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
                           sizex=None, sizey=None, level=1):
        """Extracts the pixel values from the raster in HEX format"""
        sizex = sizex or self.cols
        sizey = sizey or self.rows
        level_ts = self.tilesize*level

        # Add column padding
        if self.padding and sizex < level_ts:
            # Get rows individually
            data = [self.band.ReadRaster(startpixelx, startpixely + i, sizex, 1) for i in range(0, sizey)]
            # Convert rows to hex
            data = [binascii.hexlify(dat).upper() for dat in data]
            # Add column padding to each row
            xpad = self.nodata_hex * (level_ts - sizex)
            data = [dat + xpad for dat in data]
            # Combine rows to block
            data = ''.join(data)
        else:
            data = self.band.ReadRaster(startpixelx, startpixely, sizex, sizey)
            data = binascii.hexlify(data).upper()

        # Add row padding
        if self.padding and sizey < level_ts:
            ypad = self.nodata_hex * level_ts
            data += ypad * (level_ts - sizey)

        return data

    def bin2hex(self, fmt, data):
        """Converts binary data to HEX, using little-endian byte order"""
        return binascii.hexlify(struct.pack('<' + fmt, data)).upper()

    def rescale_tile(self, tile, level):
        """Returns sql string for rescaling a tile"""
        # Get pixelsize in raster units
        pixelsize = (self.geotransform[1], self.geotransform[5])

        # Rescale raster using postgis
        cursor = connection.cursor()
        sql = "SELECT ST_Rescale('{0}', {1}) AS rast"\
              .format(tile, pixelsize[0]*level, pixelsize[1]*level)
        cursor.execute(sql)

        return cursor.fetchone()[0]

    def create_tiles(self, level):
        """
        Creates tiles for a certain overview level by rescaling raster to the
        corresponding pixel size.
        """
        # Select srid based on level
        level_srid = self.global_srid if level == 0 else self.rasterlayer.srid

        # Store orig level in case its zero, set level to one in that case
        orig_level = level
        level = 1 if level == 0 else level

        # Setup tile size in pixel depending on level
        level_ts = self.tilesize*level

        # Create corresponding blocks
        for yblock in range(0, self.rows, level_ts):
            if yblock + level_ts < self.rows:
                numRows = level_ts
            else:
                numRows = self.rows - yblock
            
            for xblock in range(0, self.cols, level_ts):
                if xblock + level_ts < self.cols:
                    numCols = level_ts
                else:
                    numCols = self.cols - xblock
                
                # Calculate raster tile origin
                xorigin = self.originX + self.pixelWidth*xblock
                yorigin = self.originY + self.pixelHeight*yblock

                # Raster header
                if self.padding:
                    rasterheader = self.get_raster_header(xorigin, yorigin, level_ts, level_ts, orig_level)
                else:
                    rasterheader = self.get_raster_header(xorigin, yorigin, numCols, numRows, orig_level)

                # Raster band header
                bandheader = self.get_band_header()

                # Raster body content
                data = self.get_raster_content(xblock, yblock, numCols, numRows, level)

                # Combine headers with data for inserting into postgis
                data = rasterheader + bandheader + data

                # For overview levels, rescale raster
                if(level > 1):
                    data = self.rescale_tile(data, level)

                # Create raster tile
                RasterTile.objects.create(
                    rast=data,
                    rasterlayer=self.rasterlayer,
                    filename=self.rastername,
                    level=orig_level)

    def parse_raster_layer(self):
        """
        This function pushes the raster data from the Raster Layer into the
        RasterTile table, in tiles of 100x100 pixels.
        """
        # Clean previous parse log
        self.log('Started parsing raster file', reset=True)

        self.get_raster_file()
        self.open_raster_file()

        # Remove existing tiles for this layer before loading new ones
        self.rasterlayer.rastertile_set.all().delete()

        # Drop current raster constraints before adding more data
        cursor = connection.cursor()
        cursor.execute("SELECT DropRasterConstraints("\
                       "'raster_rastertile'::name,'rast'::name)")

        # Create tiles in original projection and resolution
        self.create_tiles(0)

        # Open raster in reprojected version
        self.open_raster_file(reproject=True)

        # Create tiles including pyramid in global srid
        for level in self.overview_levels:
            self.create_tiles(level)

        # Set raster constraints
        cursor.execute("SELECT AddRasterConstraints("\
                       "'raster_rastertile'::name,'rast'::name)")

        # Vacuum table
        cursor.execute('VACUUM ANALYZE "raster_rastertile"')

        # Log success of parsing
        self.log('Successfully finished parsing patch collection')

        # Remove tempdir with source file
        shutil.rmtree(self.tmpdir)
