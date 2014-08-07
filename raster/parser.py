import os, tempfile, shutil, subprocess, datetime

from django.db import connection

from raster.models import RasterTile

# sudo apt-get install python-gdal
import gdal, gdalconst
from gdalconst import GA_ReadOnly, GA_Update
import binascii
import struct

GDALDATA2WKTPIXEL = {
    gdalconst.GDT_Byte: 4, gdalconst.GDT_Int16: 5,
    gdalconst.GDT_UInt16: 6, gdalconst.GDT_Int32: 7,
    gdalconst.GDT_UInt32: 8, gdalconst.GDT_Float32: 10,
    gdalconst.GDT_Float64: 11
    }

HEXTYPES = {4: 'B', 5: 'h', 6: 'H', 7: 'i', 8: 'I', 10: 'f', 11: 'd'}

BLOCKSIZE = 100

def bin2hex(fmt, data):
    """Converts binary data to HEX."""
    return binascii.hexlify(struct.pack('<' +fmt, data)).upper()

def parse_raster_layer(rasterlayer):
    """
    This function pushes the raster data from the Raster Layer into the
    RasterTile table, in tiles of 100x100 pixels.
    """
    # Clean previous parse log
    now = '[{0}] '.format(datetime.datetime.now().strftime('%Y-%m-%d %T'))
    rasterlayer.parse_log = now + 'Started parsing raster file\n'
    rasterlayer.save()

    # Create tempdir for raster file and get raster file name
    tmpdir = tempfile.mkdtemp()
    rastername = os.path.basename(rasterlayer.rasterfile.name)

    # Access rasterfile and store locally
    try:
        rasterfile = open(os.path.join(tmpdir, rastername), 'wb')
        for chunk in rasterlayer.rasterfile.chunks():
            rasterfile.write(chunk)
        rasterfile.close()
    except IOError:
        rasterlayer.parse_log += 'Error: Library error for download\n'
        rasterlayer.save()
        shutil.rmtree(tmpdir)
        return

    # Remove existing tiles for this layer before loading new ones
    rasterlayer.rastertile_set.all().delete()

    # Drop current raster constraints before adding more data
    cursor = connection.cursor()
    cursor.execute(
        "SELECT DropRasterConstraints('raster_rastertile'::name,'rast'::name)")

    # Open raster file
    dataset = gdal.Open(os.path.join(tmpdir, rastername), GA_ReadOnly)
    band = dataset.GetRasterBand(1)
    geotransform = dataset.GetGeoTransform()

    # Get raster meta info
    cols = dataset.RasterXSize
    rows = dataset.RasterYSize
    bands = dataset.RasterCount
    originX = geotransform[0]
    originY = geotransform[3]
    pixelWidth = geotransform[1]
    pixelHeight = geotransform[5]

    # Create corresponding blocks
    # for xblock in range(0, rows, blocksize):
    #     if xblock + blocksize < rows:
    #         numRows = blocksize
    #     else:
    #         numRows = rows - xblock
        
    #     for yblock in range(0, cols, blocksize):
    #         if yblock + blocksize < cols:
    #           numCols = blocksize
    #         else:
    #               numCols = cols - yblock
        
    #         xorigin = originX + pixelWidth*xblock
    #         yorigin = originY + pixelHeight*yblock

    #         headerdata = get_raster_header(xulp, yulp, 1, blocksize, geotransform)
    #         check_hex(headerdata)
    #         rasterdata = band.ReadRaster(yblock, xblock, numCols, numRows)
    #         rasterdata2 = binascii.hexlify(rasterdata).upper()
    #         check_hex(rasterdata)
    #         check_hex(rasterdata2)
    #         data = headerdata + rasterdata2

    ### RASTER HEADER
    header = ''
    # Endiannes (little endian)
    header += bin2hex('B', 1)
    # Version
    header += bin2hex('H', 0)
    # Number of bands    
    header += bin2hex('H', 1)

    # Georeference
    header += bin2hex('d', geotransform[1]) # Scale x
    header += bin2hex('d', geotransform[5]) # Scale y
    header += bin2hex('d', geotransform[0]) # Origin x
    header += bin2hex('d', geotransform[3]) # Origin y
    header += bin2hex('d', geotransform[2]) # Skew x
    header += bin2hex('d', geotransform[4]) # Skew y
    header += bin2hex('i', int(rasterlayer.srid))
    
    # Number of columns and rows
    header += bin2hex('H', cols)
    header += bin2hex('H', rows)

    ### BAND HEADER
    # Encode pixel type
    pixtype = GDALDATA2WKTPIXEL.get(band.DataType)

    # Set the pixeltype and HasNodata bit
    header += bin2hex('B', pixtype + 64)
    
    # Encode nodata value
    header += bin2hex(HEXTYPES.get(pixtype), int(rasterlayer.nodata))

    ### RASTER BODY
    data = band.ReadRaster(0, 0, cols, rows)
    data = binascii.hexlify(data).upper()
    data = header + data

    # Create raster tile
    RasterTile.objects.create(rast=data, rasterlayer=rasterlayer, filename=rastername)

    # Set raster constraints
    cursor.execute(
        "SELECT AddRasterConstraints('raster_rastertile'::name,'rast'::name)")

    # Vacuum table
    cursor.execute('VACUUM ANALYZE "raster_rastertile"')

    # Finish message in parse log and save
    now = '[{0}] '.format(datetime.datetime.now().strftime('%Y-%m-%d %T'))
    rasterlayer.parse_log += now + 'Finished parsing patch collection'
    rasterlayer.save()

    # Remove tempdir with source file
    shutil.rmtree(tmpdir)
