import os, tempfile, shutil, datetime, struct, binascii

from osgeo import gdal
from osgeo.gdalconst import GA_ReadOnly, GDT_Byte, GDT_Int16, GDT_UInt16, GDT_Int32,\
    GDT_UInt32, GDT_Float32, GDT_Float64

from django.db import connection
from django.conf import settings

from raster.models import RasterTile

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
            4: 'B', 5: 'h', 6: 'H', 7: 'i', 8: 'I', 10: 'f', 11: 'd'}

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

    def open_raster_file(self):
        """Opens the raster file through gdal and extracts data values"""
        # Open raster file
        self.dataset = gdal.Open(os.path.join(self.tmpdir, self.rastername), GA_ReadOnly)
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

    def get_raster_header(self, originx=None, originy=None, sizex=None, sizey=None):
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
        header += self.bin2hex('i', int(self.rasterlayer.srid))
        
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

        return data

    def bin2hex(self, fmt, data):
        """Converts binary data to HEX, using little-endian byte order"""
        return binascii.hexlify(struct.pack('<' + fmt, data)).upper()

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

        # Create corresponding blocks
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

                # Combine headers with data for inserting into postgis
                data = rasterheader + bandheader + data

                # Create raster tile
                RasterTile.objects.create(
                    rast=data,
                    rasterlayer=self.rasterlayer,
                    filename=self.rastername)

        # Set raster constraints
        cursor.execute("SELECT AddRasterConstraints("\
                       "'raster_rastertile'::name,'rast'::name)")

        # Vacuum table
        cursor.execute('VACUUM ANALYZE "raster_rastertile"')

        # Log success of parsing
        self.log('Successfully finished parsing patch collection')

        # Remove tempdir with source file
        shutil.rmtree(self.tmpdir)
