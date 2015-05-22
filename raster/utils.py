import numpy
from PIL import Image

"""
Structure of a PostGIS Raster Header

http://postgis.net/docs/RT_ST_MakeEmptyRaster.html
"""
HEADER_NAMES = [
    'endianness',
    'version',
    'nr_of_bands',
    'scalex',
    'scaley',
    'originx',
    'originy',
    'skewx',
    'skewy',
    'srid',
    'sizex',
    'sizey'
]

HEADER_STRUCTURE = 'B H H d d d d d d i H H'

"""
GDAL

Pixel data types

http://www.gdal.org/gdal_8h.html#a22e22ce0a55036a96f652765793fb7a4

GDT_Unknown  - Unknown or unspecified type
GDT_Byte     - Eight bit unsigned integer
GDT_UInt16   - Sixteen bit unsigned integer
GDT_Int16    - Sixteen bit signed integer
GDT_UInt32   - Thirty two bit unsigned integer
GDT_Int32    - Thirty two bit signed integer
GDT_Float32  - Thirty two bit floating point
GDT_Float64  - Sixty four bit floating point
GDT_CInt16   - Complex Int16
GDT_CInt32   - Complex Int32
GDT_CFloat32 - Complex Float32
GDT_CFloat64 - Complex Float64
"""

GDAL_PIXEL_TYPES = {
    0: 'GDT_Unknown',
    1: 'GDT_Byte',
    2: 'GDT_UInt16',
    3: 'GDT_Int16',
    4: 'GDT_UInt32',
    5: 'GDT_Int32',
    6: 'GDT_Float32',
    7: 'GDT_Float64',
    8: 'GDT_CInt16',
    9: 'GDT_CInt32',
    10: 'GDT_CFloat32',
    11: 'GDT_CFloat64'
}

GDAL_PIXEL_TYPES_INV = {v: k for k, v in GDAL_PIXEL_TYPES.items()}

GDAL_PIXEL_TYPES_UNISGNED = [1, 2, 4]

"""
POSTGIS

Band Pixel Type

ftp://ftp.refractions.net/pub/refractions/postgis/docs/html/RT_ST_BandPixelType.html
http://svn.osgeo.org/postgis/spike/wktraster/doc/RFC2-WellKnownBinaryFormat

1BB   - 1-bit boolean
2BUI  - 2-bit unsigned integer
4BUI  - 4-bit unsigned integer
8BSI  - 8-bit signed integer
8BUI  - 8-bit unsigned integer
16BSI - 16-bit signed integer
16BUI - 16-bit unsigned integer
32BSI - 32-bit signed integer
32BUI - 32-bit unsigned integer
32BF  - 32-bit float
64BF  - 64-bit float
"""

POSTGIS_PIXEL_TYPES = {
    0: '1BB',
    1: '2BUI',
    2: '4BUI',
    3: '8BSI',
    4: '8BUI',
    5: '16BSI',
    6: '16BUI',
    7: '32BSI',
    8: '32BUI',
    9: '32BF',
    10: '64BF'
}

POSTGIS_PIXEL_TYPES_INV = {v: k for k, v in POSTGIS_PIXEL_TYPES.items()}

GDAL_TO_POSTGIS = {
    'GDT_Unknown': None,
    'GDT_Byte': '8BUI',
    'GDT_UInt16': '16BUI',
    'GDT_Int16': '16BSI',
    'GDT_UInt32': '32BUI',
    'GDT_Int32': '32BSI',
    'GDT_Float32': '32BF',
    'GDT_Float64': '64BF',
    'GDT_CInt16': None,
    'GDT_CInt32': None,
    'GDT_CFloat32': None,
    'GDT_CFloat64': None
}

POSTGIS_TO_GDAL = {
    '1BB': None,
    '2BUI': None,
    '4BUI': None,
    '8BSI': None,
    '8BUI': 'GDT_Byte',
    '16BSI': 'GDT_Int16',
    '16BUI': 'GDT_UInt16',
    '32BSI': 'GDT_Int32',
    '32BUI': 'GDT_UInt32',
    '32BF': 'GDT_Float32',
    '64BF': 'GDT_CFloat64'
}

"""
PYTHON

Python Struct Types

https://docs.python.org/2/library/struct.html#format-characters

Format, C Type          Python Type Standard Size
b - signed char         integer     1
B - unsigned char       integer     1
? - _Bool               bool        1
h - short               integer     2
H - unsigned short      integer     2
i - int                 integer     4
I - unsigned int        integer     4
l - long                integer     4
L - unsigned long       integer     4
q - long long           integer     8
Q - unsigned long long  integer     8
f - float               float       4
d - double              float       8
"""

STRUCT_SIZE = {
    'b': 1,
    'B': 1,
    '?': 1,
    'h': 2,
    'H': 2,
    'i': 4,
    'I': 4,
    'l': 4,
    'L': 4,
    'f': 4,
    'd': 8
}

GDAL_TO_STRUCT = {
    'GDT_Unknown': None,
    'GDT_Byte': 'B',
    'GDT_UInt16': 'H',
    'GDT_Int16': 'h',
    'GDT_UInt32': 'L',
    'GDT_Int32': 'l',
    'GDT_Float32': 'f',
    'GDT_Float64': 'd',
    'GDT_CInt16': None,
    'GDT_CInt32': None,
    'GDT_CFloat32': None,
    'GDT_CFloat64': None
}

POSTGIS_TO_STRUCT = {
    '1BB': '?',
    '2BUI': None,
    '4BUI': None,
    '8BSI': 'b',
    '8BUI': 'B',
    '16BSI': 'h',
    '16BUI': 'H',
    '32BSI': 'l',
    '32BUI': 'L',
    '32BF': 'f',
    '64BF': 'd'
}


def convert_pixeltype(data, source, target):
    """
    Utility to convert pixel types between GDAL, PostGIS and Python Struct
    """
    if source == 'gdal':
        data = GDAL_PIXEL_TYPES[data]
        if target == 'postgis':
            return POSTGIS_PIXEL_TYPES_INV[GDAL_TO_POSTGIS[data]]
        elif target == 'struct':
            return GDAL_TO_STRUCT[data]

    elif source == 'postgis':
        data = POSTGIS_PIXEL_TYPES[data]
        if target == 'gdal':
            return GDAL_PIXEL_TYPES_INV[POSTGIS_TO_GDAL[data]]
        elif target == 'struct':
            return POSTGIS_TO_STRUCT[data]

IMG_FORMATS = {'.png': 'PNG', '.jpg': 'JPEG'}


def hex_to_rgba(value, alpha=255):
    value = value.lstrip('#')
    lv = len(value)
    rgb = tuple(int(value[i:i + lv // 3], 16) for i in range(0, lv, lv // 3))
    return rgb + (alpha, )


def raster_to_image(raster, colormap, band=0):
    """
    Creates an python image from pixel values of a GDALRaster.
    The input is a dictionary that maps pixel values to RGBA UInt8 colors.
    """
    # Get data as 1D array
    dat = raster.bands[band].data().ravel()

    # Create zeros array
    rgba = numpy.zeros((dat.shape[0], 4), dtype='uint8')

    # Replace matched rows with colors
    for key, color in colormap.items():
        try:
            # Try to use the key as number directly
            key = float(key)
            rgba[dat == key] = color
        except ValueError:
            # Otherwise use it as numpy expression directly (replacing x with dat)
            key = key.replace('x', 'dat')
            selector = eval(key)
            rgba[selector] = color

    # Reshape array to image size
    rgba = rgba.reshape(raster.height, raster.width, 4)

    # Create image from array
    return Image.fromarray(rgba)
