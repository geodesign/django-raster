import struct, binascii, numpy
from PIL import Image
from osgeo import gdal, osr, gdalconst

from django.core.exceptions import ValidationError

from utils import convert_pixeltype, HEADER_STRUCTURE, HEADER_NAMES,\
    GDAL_PIXEL_TYPES, GDAL_PIXEL_TYPES_UNISGNED, STRUCT_SIZE


class OGRRaster(object):
    """Django Raster Object"""

    def __init__(self, data, srid=None):

        if isinstance(data, str):
            self.set_ptr_from_postgis_raster(data)
        elif isinstance(data, gdal.Dataset):            
            self.ptr = data

            # If srid is provided explicitly, override projection
            # Otherwise make sure projection is properly defined
            if srid:
                self.set_projection(srid)
            elif not self.srid:
                raise ValidationError('Raster SRID could not be determined, please specify.')
        else:
            raise ValidationError('Raster must be a string or GdalRaster.')

    # Data parser methods
    def pack(self, structure, data):
        """Packs data into binary data in little endian format"""
        return binascii.hexlify(struct.pack('<' + structure, *data)).upper()

    def unpack(self, structure, data):
        """Unpacks hexlified binary data in little endian format."""
        return struct.unpack('<' + structure, binascii.unhexlify(data))

    def chunk(self, data, index):
        """Splits string data into two halfs at the input index"""
        return data[:index], data[index:]

    def set_ptr_from_postgis_raster(self, data):
        """Returns a gdal in-memory raster from a PostGIS Raster String"""

        # Split raster header from data
        header, data = self.chunk(data, 122)

        # Process header
        header =  self.unpack(HEADER_STRUCTURE, header)
        header = dict(zip(HEADER_NAMES, header))

        # Process bands
        bands = []
        for i in range(header['nr_of_bands']):

            # Get pixel type for this band
            pixeltype, data = self.chunk(data, 2)
            pixeltype = self.unpack('B', pixeltype)[0]

            # Get band nodata value if exists
            if pixeltype > 64:
                pixeltype -= 64
                has_nodata = True
            else:
                has_nodata = False

            # String with hex type name for unpacking
            pack_type = convert_pixeltype(pixeltype, 'postgis', 'struct')

            # Length in bytes of the hex type
            pixeltype_len = STRUCT_SIZE[pack_type]

            nodata, data = self.chunk(data, 2 * pixeltype_len)
            nodata = self.unpack(pack_type, nodata)[0]

            if not has_nodata:
                nodata = None

            # PostGIS datatypes mapped to Gdalconstants data types
            pixeltype_gdal = convert_pixeltype(pixeltype, 'postgis', 'gdal')

            # Chunnk and unpack band data
            nr_of_pixels = header['sizex'] * header['sizey']
            band_data, data = self.chunk(data, 2 * nr_of_pixels)
            band_data = self.unpack(pack_type * nr_of_pixels, band_data)

            # Convert data to numpy 2d array
            band_data_array = numpy.array(band_data)
            band_data_array = band_data_array.reshape((header['sizex'], 
                                                       header['sizey']))

            bands.append({'type': pixeltype_gdal, 'nodata': nodata,
                          'data': band_data, 'array': band_data_array})

        # Check that all bands have the same pixeltype
        if len(set([x['type'] for x in bands])) != 1:
            raise ValidationError("Band pixeltypes of  are not all equal.")

        # Create gdal in-memory raster
        driver = gdal.GetDriverByName('MEM')
        self.ptr = driver.Create('OGRRaster', header['sizex'], header['sizey'], 
                            header['nr_of_bands'], bands[0]['type'])

        # Set GeoTransform
        self.ptr.SetGeoTransform((
            header['originx'], header['scalex'], header['skewx'],
            header['originy'], header['skewy'], header['scaley']
        ))

        # Set projection
        self.set_projection(header['srid'])

        # Write bands to gdal raster
        for i in range(header['nr_of_bands']):
            # Get band
            gdalband = self.ptr.GetRasterBand(i + 1)

            # Write data to band
            gdalband.WriteArray(bands[i]['array'])

            # Set band nodata value if available
            if bands[i]['nodata']:
                gdalband.SetNoDataValue(bands[i]['nodata'])

    def to_postgis_raster(self):
        """Retruns the raster as postgis raster string"""

        # Get GDAL geotransform for header data
        gt = self.ptr.GetGeoTransform()

        # Get other required header data
        num_bands = self.ptr.RasterCount

        # Setup raster header as array, first two numbers are 
        # endianness and version, which are fixed by postgis at the moment
        rasterheader = (1, 0, num_bands, gt[1], gt[5], gt[0], gt[3], 
                  gt[2], gt[4], self.srid, self.ptr.RasterXSize,
                  self.ptr.RasterYSize)

        # Pack header into binary data
        result = self.pack(HEADER_STRUCTURE, rasterheader)

        # Pack band data, add to result
        for i in range(num_bands):
            # Get band
            band = self.ptr.GetRasterBand(i + 1)

            # Set base structure for raster header - pixeltype
            structure = 'B'

            # Get band header data
            nodata = band.GetNoDataValue()
            pixeltype = convert_pixeltype(band.DataType, 'gdal', 'postgis')

            if nodata < 0 and pixeltype in GDAL_PIXEL_TYPES_UNISGNED:
                nodata = abs(nodata)

            if nodata is not None:
                # Setup packing structure for header with nodata
                structure += convert_pixeltype(pixeltype, 'postgis', 'struct')

                # Add flag to point to existing nodata type
                pixeltype += 64

            # Pack header
            bandheader = self.pack(structure, (pixeltype, nodata))

            # Read raster as binary and hexlify
            data = band.ReadRaster()
            data = binascii.hexlify(data).upper()

            # Add band to result string
            result += bandheader + data

        # Return PostGIS Raster String
        return result

    # GDAL Raster spatial methods
    @property
    def srid(self):
        """Returns srid of raster"""
        prj = self.ptr.GetProjectionRef()
        srs = osr.SpatialReference(prj)

        if srs.IsProjected():
            return int(srs.GetAuthorityCode('PROJCS'))
        else:
            return int(srs.GetAuthorityCode('GEOGCS'))

    @property
    def upperleftx(self):
        """X coordinate of origin (upper left corner)"""
        return self.ptr.GetGeoTransform()[0]

    @property
    def upperlefty(self):
        """Y coordinate of origin (upper left corner)"""
        return self.ptr.GetGeoTransform()[3]

    @property
    def scalex(self):
        """Scale of pixels in X directon"""
        return self.ptr.GetGeoTransform()[1]

    @property
    def scaley(self):
        """Scale of pixels in Y directon"""
        return self.ptr.GetGeoTransform()[5]

    @property
    def skewx(self):
        """Skew of pixels in X direction"""
        return self.ptr.GetGeoTransform()[2]

    @property
    def skewy(self):
        """Skew of pixels in Y directionX"""
        return self.ptr.GetGeoTransform()[4]

    @property
    def metadata(self):
        """Dictionary of meta data of the raster"""
        return {
            'upperleftx': self.upperleftx,
            'upperlefty': self.upperlefty,
            'scalex': self.scalex,
            'scaley': self.scaley,
            'skewx': self.skewx,
            'skewy': self.skewy
        }

    @property
    def nr_of_pixels(self):
        return self.ptr.RasterXSize * self.ptr.RasterYSize

    def value_count(self, band=1):
        """Value count statistics for this raster"""
        data = self.ptr.GetRasterBand(band).ReadAsArray()
        unique, counts = numpy.unique(data, return_counts=True)
        return numpy.asarray((unique, counts)).T

    def pixeltype(self, band=1, as_text=False):
        datatype = self.ptr.GetRasterBand(band).DataType
        if as_text:
            return GDAL_PIXEL_TYPES[datatype]
        else:
            return datatype

    def array(self, band=1):
        """Returns band data as numpy array"""
        return numpy.array(self.ptr.GetRasterBand(band).ReadAsArray())

    def nodata_value(self, band=1):
        """Returns the nodata value for a band"""
        bnd = self.ptr.GetRasterBand(band)
        return bnd.GetNoDataValue()

    def set_projection(self, srid):
        """Updates projection to given srid"""
        srs = osr.SpatialReference()
        srs.ImportFromEPSG(srid)
        self.ptr.SetProjection(srs.ExportToWkt())

    def img(self, colormap, band=1):
        """
        Creates an python image from pixel values. Currently works for
        discrete colormaps. The input is a dictionary that maps pixel
        values to RGBA UInt8 colors.
        """
        # Get data as 1D array
        dat = self.array()
        dat = dat.reshape(dat.shape[0]*dat.shape[1],)

        # Create zeros array
        rgba = numpy.zeros((self.nr_of_pixels, 4), dtype='uint8')

        # Replace matched rows with colors
        for key, color in colormap.items():
            rgba[dat == key] = color

        # Reshape array to image size
        rgba = rgba.reshape(self.ptr.RasterYSize, self.ptr.RasterXSize, 4)

        # Create image from array
        return Image.fromarray(rgba)
