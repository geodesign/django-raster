from math import pi

IMG_FORMATS = {'.png': 'PNG', '.jpg': 'JPEG'}

WEB_MERCATOR_SRID = 3857

WEB_MERCATOR_WORLDSIZE = 2 * pi * 6378137

WEB_MERCATOR_TILESHIFT = WEB_MERCATOR_WORLDSIZE / 2.0

WEB_MERCATOR_TILESIZE = 256

GLOBAL_MAX_ZOOM_LEVEL = 18

GDAL_TO_NUMPY_PIXEL_TYPES = {
    1: 'UInt8',  # Eight bit unsigned integer
    2: 'UInt16',  # Sixteen bit unsigned integer
    3: 'Int16',  # Sixteen bit signed integer
    4: 'UInt32',  # Thirty-two bit unsigned integer
    5: 'Int32',  # Thirty-two bit signed integer
    6: 'Float32',  # Thirty-two bit floating point
    7: 'Float64',  # Sixty-four bit floating point
}

ALGEBRA_PIXEL_TYPE_GDAL = 7
ALGEBRA_PIXEL_TYPE_NUMPY = 'Float64'
