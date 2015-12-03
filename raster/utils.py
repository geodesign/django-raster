import numpy
from PIL import Image

from raster.exceptions import RasterException

from .formulas import FormulaParser

IMG_FORMATS = {'.png': 'PNG', '.jpg': 'JPEG'}


def hex_to_rgba(value, alpha=255):
    """
    Converts a HEX color string to a RGBA 4-tuple.
    """
    value = value.lstrip('#')
    lv = len(value)
    try:
        rgb = tuple(int(value[i:i + lv // 3], 16) for i in range(0, lv, lv // 3))
    except ValueError:
        raise RasterException('Invalid color, could not convert hex to rgb.')

    return rgb + (alpha, )


def band_data_to_image(band_data, colormap):
    """
    Creates an python image from pixel values of a GDALRaster.
    The input is a dictionary that maps pixel values to RGBA UInt8 colors.
    """
    parser = FormulaParser()

    # Get data as 1D array
    dat = band_data.ravel()

    # Create zeros array
    rgba = numpy.zeros((dat.shape[0], 4), dtype='uint8')

    # Replace matched rows with colors
    stats = {}
    for key, color in colormap.items():
        orig_key = key
        try:
            # Try to use the key as number directly
            key = float(key)
            selector = dat == key
            rgba[selector] = color
        except ValueError:
            # Otherwise use it as numpy expression directly
            selector = parser.evaluate_formula(key, {'x': dat})
            rgba[selector] = color
        stats[orig_key] = int(numpy.sum(selector))

    # Reshape array to image size
    rgba = rgba.reshape(band_data.shape[0], band_data.shape[1], 4)

    # Create image from array
    img = Image.fromarray(rgba)

    return img, stats
