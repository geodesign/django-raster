import os, tempfile, zipfile, shutil, datetime, struct, binascii, glob
from osgeo import gdal, osr
from osgeo.gdalconst import GA_ReadOnly, GDT_Byte, GDT_Int16, GDT_UInt16, GDT_Int32,\
    GDT_UInt32, GDT_Float32, GDT_Float64
from math import pi

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
            # return True
        except:
            shutil.rmtree(self.tmpdir)
            self.log('Error: Library error for download')
            return False

        # If the raster file is compress, decompress it
        fileName, fileExtension = os.path.splitext(self.rastername)
        if fileExtension == '.zip':
            try:
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
            except:
                shutil.rmtree(self.tmpdir)
                self.log('Error: Could not open zipfile')
                return False

        return True

    def open_raster_file(self):
        """Opens the raster file through gdal and extracts data values"""
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

    def create_tiles(self):
        """
        Creates base tiles in original projection. These tiles are not intended
        for rendering but for analysis in the original projection. This makes
        value count statistics etc more accurate.
        """

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

                # Create raster tile
                RasterTile.objects.create(
                    rast=data,
                    rasterlayer=self.rasterlayer,
                    filename=self.rastername,
                    is_base=True
                )

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
        self.create_tiles()

        # Open raster in reprojected version
        self.open_raster_file()

        # Create base tiles in original projection
        self.create_tiles()

        # Setup TMS aligned tiles in world mercator
        self.make_tms_tiles()

        # Set raster constraints
        cursor.execute("SELECT AddRasterConstraints("\
                       "'raster_rastertile'::name,'rast'::name)")

        # Vacuum table
        cursor.execute('VACUUM ANALYZE "raster_rastertile"')

        # Log success of parsing
        self.log('Successfully finished parsing patch collection')

        # Remove tempdir with source file
        shutil.rmtree(self.tmpdir)

    def get_max_zoom(self, scale):
        res = 2 * pi * 6378137
        shift = res / 2.0

        zoom_scales = [res/2**i/256 for i in range(1,18)]
        index = min(range(len(zoom_scales)), key=lambda i: abs(zoom_scales[i] - scale)) + 1

        return index

    def get_tile_range(self, bbox, z):
        res = 2 * pi * 6378137
        shift = res / 2.0
        scale = res / 2**z
        return [
            int((bbox[0] + shift)/scale),
            int((shift - bbox[3])/scale),
            int((bbox[2] + shift)/scale),
            int((shift - bbox[1])/scale)
        ]

    def get_tile_bounds(self, x, y, z):
        """
        Calculates tile bounding box from Tile Map Service XYZ indices.
        """
        # Setup scale factor for bounds calculations
        res = 2 * pi * 6378137
        shift = res / 2.0
        scale = res / 2**z

        # Calculate bounds
        minx = x * scale - shift
        maxx = (x+1) * scale - shift
        miny = shift - (y+1) * scale
        maxy = shift - y * scale

        return [minx, miny, maxx, maxy]

    def make_tms_tiles(self):
        from django.contrib.gis.geos import Polygon
        scale = self.rasterlayer.pixelsize()[0]
        bbox = self.rasterlayer.extent()
        zoom = self.get_max_zoom(scale)
        for iz in range(10, zoom + 1):
            indexrange = self.get_tile_range(bbox, iz)
            for ix in range(indexrange[0], indexrange[2]+1):
                for iy in range(indexrange[1], indexrange[3]+1):
                    bounds = self.get_tile_bounds(ix, iy, iz)
                    geom = Polygon.from_bbox(bounds)

                    var = """SELECT
                    ST_Clip(
                        ST_Transform(
                            ST_Union(rast),
                            ST_MakeEmptyRaster({nrpixel}, {nrpixel}, {upperleftx}, {upperlefty}, {scalex}, {scaley}, {skewx}, {skewy}, {srid})
                        ),
                        ST_GeomFromEWKT('SRID={srid};{geomwkt}')
                    )
                    FROM raster_rastertile 
                    WHERE tilez IS NULL
                    AND rasterlayer_id={rasterlayer}
                    AND rast && ST_Transform(ST_GeomFromEWKT('SRID={srid};{geomwkt}'), ST_SRID(rast))
                    """

                    sql = var.format(
                        nrpixel=256,
                        upperleftx=bounds[0],
                        upperlefty=bounds[3],
                        scalex=(bounds[2]-bounds[0])/256,
                        scaley=-(bounds[3]-bounds[1])/256,
                        skewx=0,
                        skewy=0,
                        srid=3857,
                        geomwkt=geom.wkt,
                        level=0,
                        rasterlayer=self.rasterlayer.id,
                    )

                    cursor=connection.cursor()
                    cursor.execute(sql)
                    data = cursor.fetchone()[0]

                    RasterTile.objects.create(
                        rast=data,
                        rasterlayer=self.rasterlayer,
                        filename=self.rastername,
                        tilex=ix,
                        tiley=iy,
                        tilez=iz
                    )
