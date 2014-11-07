import struct, binascii, numpy
from osgeo import gdal, osr, gdalconst

from django.core.exceptions import ValidationError

RASTER_HEADER_STRUCTURE = 'B H H d d d d d d i H H'

RASTER_HEADER_NAMES = [
    'endianness', 'version', 'nr_of_bands', 'scalex', 'scaley',
    'originx', 'originy', 'skewx', 'skewy', 'srid', 'sizex', 'sizey'
]

HEXTYPES = {4: 'B', 5: 'h', 6: 'H', 7: 'i', 8: 'I', 10: 'f', 11: 'd'}

HEXLENGTHS = {'B': 1, 'h': 2, 'H': 2, 'i': 4, 'I': 4, 'f': 4, 'd': 8}

GDALTYPES = {
        4: gdalconst.GDT_Byte, 5: gdalconst.GDT_Int16, 
        6: gdalconst.GDT_UInt16, 7: gdalconst.GDT_Int32,
        8: gdalconst.GDT_UInt32, 10: gdalconst.GDT_Float32,
        11: gdalconst.GDT_Float64
}

GDALTYPES_UNISGNED = [gdalconst.GDT_Byte, gdalconst.GDT_UInt16, gdalconst.GDT_UInt32]

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
        header =  self.unpack(RASTER_HEADER_STRUCTURE, header)
        header = dict(zip(RASTER_HEADER_NAMES, header))

        # Process bands
        bands = []
        for i in range(header['nr_of_bands']):
            # Get pixel type for this band
            pixeltype, data = self.chunk(data, 2)

            # This assumes a nodata value is always specified
            # TODO: Handle rasters without nodata values
            pixeltype = self.unpack('B', pixeltype)[0] - 64

            # String with hex type name for unpacking
            pixeltype_hex = HEXTYPES[pixeltype]

            # Length in bytes of the hex type
            pixeltype_len = HEXLENGTHS[pixeltype_hex]

            # PostGIS datatypes mapped to Gdalconstants data types
            pixeltype_gdal = GDALTYPES[pixeltype]

            # Get band nodata value
            nodata, data = self.chunk(data, 2 * pixeltype_len)
            nodata = self.unpack(pixeltype_hex, nodata)[0]

            # Chunnk and unpack band data
            nr_of_pixels = header['sizex'] * header['sizey']
            band_data, data = self.chunk(data, 2 * nr_of_pixels)
            band_data = self.unpack(pixeltype_hex * nr_of_pixels, band_data)

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
            gdalband = self.ptr.GetRasterBand(i + 1)
            gdalband.SetNoDataValue(bands[i]['nodata'])
            gdalband.WriteArray(bands[i]['array'])

    def to_postgis_raster(self):
        """Retruns the raster as postgis raster string"""

        # Get GDAL geotransform for header data
        gt = self.ptr.GetGeoTransform()

        # Get other required header data
        num_bands = self.ptr.RasterCount
        pixelcount = self.ptr.RasterXSize * self.ptr.RasterYSize

        # Setup raster header as array, first two numbers are 
        # endianness and version, which are fixed by postgis at the moment
        rasterheader = (1, 0, num_bands, gt[1], gt[5], gt[0], gt[3], 
                  gt[2], gt[4], self.srid, self.ptr.RasterXSize,
                  self.ptr.RasterYSize)

        # Pack header into binary data
        result = self.pack(RASTER_HEADER_STRUCTURE, rasterheader)

        # Pack band data, add to result
        for i in range(num_bands):
            # Get band
            band = self.ptr.GetRasterBand(i + 1)

            # Set base structure for raster header - pixeltype
            structure = 'B'

            # Get band header data
            nodata = band.GetNoDataValue()
            pixeltype = {v: k for k, v in GDALTYPES.items()}[band.DataType]
            if nodata < 0 and pixeltype in GDALTYPES_UNISGNED:
                nodata = abs(nodata)

            if nodata is not None:
                # Setup packing structure for header with nodata
                structure += HEXTYPES[pixeltype]
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
    def set_projection(self, srid):
        """Updates projection to given srid"""
        srs = osr.SpatialReference()
        srs.ImportFromEPSG(srid)
        self.ptr.SetProjection(srs.ExportToWkt())

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
    def value_count(self, band=1):
        """Value count statistics for this raster"""
        data = self.ptr.GetRasterBand(band).ReadAsArray()
        unique, counts = numpy.unique(data, return_counts=True)
        return numpy.asarray((unique, counts)).T
