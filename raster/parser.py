import os, tempfile, shutil, subprocess, datetime

from django.db import connection

from raster.models import RasterTile

# sudo apt-get install python-gdal
import gdal, gdalconst
from gdalconst import GA_ReadOnly, GA_Update
import binascii
import struct


class RasterLayerParser:
    """Class to parse raster layers using gdal python bindings"""
    
    def __init__(self, rasterlayer):
        self.rasterlayer = rasterlayer

        self.rastername = os.path.basename(rasterlayer.rasterfile.name)

        self.gdaldata2wktpixel = {
            gdalconst.GDT_Byte: 4, gdalconst.GDT_Int16: 5,
            gdalconst.GDT_UInt16: 6, gdalconst.GDT_Int32: 7,
            gdalconst.GDT_UInt32: 8, gdalconst.GDT_Float32: 10,
            gdalconst.GDT_Float64: 11
            }
        
        self.hextypes = {4: 'B', 5: 'h', 6: 'H', 7: 'i', 8: 'I', 10: 'f', 11: 'd'}

        self.blocksize = 100

        self.tmpdir = ''

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
            now = '[{0}] '.format(datetime.datetime.now().strftime('%Y-%m-%d %T'))
            self.rasterlayer.parse_log += now + 'Error: Library error for download\n'
            self.rasterlayer.save()
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

    def get_raster_header(self, originx=None, originy=None, allpixels=False):
        """Gets the raster header in HEX format"""

        # Get data from objects if not set by user
        originx = originx or self.geotransform[0]
        originy = originy or self.geotransform[3]
        if allpixels:
            sizex = sizex or self.cols
            sizey = sizey or self.rows
        else:
            sizex = self.blocksize
            sizey = self.blocksize

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

        # Encode pixel type
        pixtype = self.gdaldata2wktpixel.get(self.band.DataType)

        # Set the pixeltype and HasNodata bit
        header += self.bin2hex('B', pixtype + 64)
        
        # Encode nodata value
        header += self.bin2hex(self.hextypes.get(pixtype), int(self.rasterlayer.nodata))

        return header

    def get_raster_content(self, startpixelx=0, startpixely=0, allpixels=False):
        """Extracts the pixel values from the raster in HEX format"""
        if allpixels:
            sizex = sizex or self.cols
            sizey = sizey or self.rows
        else:
            sizex = self.blocksize
            sizey = self.blocksize

        data = self.band.ReadRaster(startpixelx, startpixely, sizex, sizey)
        data = binascii.hexlify(data).upper()

        return data

    def bin2hex(self, fmt, data):
        """Converts binary data to HEX."""
        return binascii.hexlify(struct.pack('<' +fmt, data)).upper()

    def parse_raster_layer(self):
        """
        This function pushes the raster data from the Raster Layer into the
        RasterTile table, in tiles of 100x100 pixels.
        """
        # Clean previous parse log
        now = '[{0}] '.format(datetime.datetime.now().strftime('%Y-%m-%d %T'))
        self.rasterlayer.parse_log = now + 'Started parsing raster file\n'
        self.rasterlayer.save()

        self.get_raster_file()
        self.open_raster_file()

        # Remove existing tiles for this layer before loading new ones
        self.rasterlayer.rastertile_set.all().delete()

        # Drop current raster constraints before adding more data
        cursor = connection.cursor()
        cursor.execute(
            "SELECT DropRasterConstraints('raster_rastertile'::name,'rast'::name)")

        # Create corresponding blocks
        for yblock in range(0, self.rows, self.blocksize):
            if yblock + self.blocksize < self.rows:
                numRows = self.blocksize
            else:
                continue
                # numRows = rows - xblock
            
            for xblock in range(0, self.cols, self.blocksize):
                if xblock + self.blocksize < self.cols:
                  numCols = self.blocksize
                else:
                    continue
                    # numCols = cols - yblock
            
                xorigin = self.originX + self.pixelWidth*xblock
                yorigin = self.originY + self.pixelHeight*yblock

                # Raster parsing
                rasterheader = self.get_raster_header(xorigin, yorigin)
                bandheader = self.get_band_header()
                data = self.get_raster_content(xblock, yblock)

                # Combine data for inserting
                data = rasterheader + bandheader + data

                # Create raster tile
                RasterTile.objects.create(rast=data, rasterlayer=self.rasterlayer, filename=self.rastername)

        # Set raster constraints
        cursor.execute(
            "SELECT AddRasterConstraints('raster_rastertile'::name,'rast'::name)")

        # Vacuum table
        cursor.execute('VACUUM ANALYZE "raster_rastertile"')

        # Finish message in parse log and save
        now = '[{0}] '.format(datetime.datetime.now().strftime('%Y-%m-%d %T'))
        self.rasterlayer.parse_log += now + 'Finished parsing patch collection'
        self.rasterlayer.save()

        # Remove tempdir with source file
        shutil.rmtree(self.tmpdir)
