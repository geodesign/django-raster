import struct, binascii
from numpy import array

from osgeo import gdal, osr, gdalconst
from django.core.exceptions import ValidationError
from django.db import models

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

class OGRRaster(object):
    """Django Raster Object"""

    def __init__(self, data, srid=3086):

        self.srid = srid

        # Validate input
        if not isinstance(data, str):
            raise ValidationError('Raster can only be a string at the moment')

        self.ptr = self.from_postgis_raster(data)

    def pack(self, structure, data):
        """Packs data into binary data in little endian format"""
        return binascii.hexlify(struct.pack('<' + structure, *data)).upper()

    def unpack(self, structure, data):
        """Unpacks hexlified binary data in little endian format."""
        return struct.unpack('<' + structure, binascii.unhexlify(data))

    def chunk(self, data, index):
        """Splits string data into two halfs at the input index"""
        return data[:index], data[index:]

    def from_postgis_raster(self, data):
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
            band_data_array = array(band_data)
            band_data_array = band_data_array.reshape((header['sizex'], 
                                                       header['sizey']))

            bands.append({'type': pixeltype_gdal, 'nodata': nodata,
                          'data': band_data, 'array': band_data_array})

        # Check that all bands have the same pixeltype
        if len(set([x['type'] for x in bands])) != 1:
            raise ValidationError("Band pixeltypes of  are not all equal.")

        # Create gdal in-memory raster
        driver = gdal.GetDriverByName('MEM')
        ptr = driver.Create('OGRRaster', header['sizex'], header['sizey'], 
                            header['nr_of_bands'], bands[0]['type'])

        # Set GeoTransform
        ptr.SetGeoTransform((
            header['originx'], header['scalex'], header['skewx'],
            header['originy'], header['skewy'], header['scaley']
        ))

        # Set projection
        srs = osr.SpatialReference()
        srs.ImportFromEPSG(header['srid'])
        ptr.SetProjection(srs.ExportToWkt())

        # Write bands to gdal raster
        for i in range(header['nr_of_bands']):
            gdalband = ptr.GetRasterBand(i + 1)
            gdalband.SetNoDataValue(bands[i]['nodata'])
            gdalband.WriteArray(bands[i]['array'])

        # Return gdal raster
        return ptr

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

            # Get band header data
            nodata = band.GetNoDataValue()
            pixeltype = {v: k for k, v in GDALTYPES.items()}[band.DataType]

            # Setup packing structure for header
            structure = 'B ' + HEXTYPES[pixeltype]

            # Pack header
            bandheader = self.pack(structure, (pixeltype + 64, nodata))

            # Read raster as binary and hexlify
            data = band.ReadRaster()
            data = binascii.hexlify(data).upper()

            # Add band to result string
            result += bandheader + data

        # Return PostGIS Raster String
        return result


class RasterField(models.Field):
    """
    Binary field that uses the raster db type to store raster data in django
    """

    description = "PostGIS Raster Field"
     
    __metaclass__ = models.SubfieldBase

    def db_type(self, connection):
        return 'raster'

    def from_db_value(self, value, connection):
        # Convert PostGIS Raster string to OGR Rasters
        if value:
            value = OGRRaster(value)

        return value

    def get_prep_value(self, value):
        value = super(RasterField, self).get_prep_value(value)

        if value is None:
            return value

        if isinstance(value, OGRRaster):
            return value.to_postgis_raster()
        elif isinstance(value, str):
            return value
        else:
            raise ValueError('Could not create raster from lookup value.')

    def to_python(self, value):
        if value is None:
            return value

        if isinstance(value, OGRRaster):
            return value

        return OGRRaster(value)
