"""
Everything required to create TMS tiles.
"""
from django.conf import settings
from raster.const import GLOBAL_MAX_ZOOM_LEVEL, WEB_MERCATOR_TILESHIFT, WEB_MERCATOR_TILESIZE, WEB_MERCATOR_WORLDSIZE


def tile_index_range(bbox, z):
    """
    Calculate the index range for a given bounding box and zoomlevel.
    """
    # Calculate tile size for given zoom level
    zscale = WEB_MERCATOR_WORLDSIZE / 2 ** z

    # Calculate overlaying tile indices
    return [
        int((bbox[0] + WEB_MERCATOR_TILESHIFT) / zscale),
        int((WEB_MERCATOR_TILESHIFT - bbox[3]) / zscale),
        int((bbox[2] + WEB_MERCATOR_TILESHIFT) / zscale),
        int((WEB_MERCATOR_TILESHIFT - bbox[1]) / zscale)
    ]


def tile_bounds(x, y, z):
    """
    Calculate the bounding box of a specific tile.
    """
    zscale = WEB_MERCATOR_WORLDSIZE / 2 ** z

    xmin = x * zscale - WEB_MERCATOR_TILESHIFT
    xmax = (x + 1) * zscale - WEB_MERCATOR_TILESHIFT
    ymin = WEB_MERCATOR_TILESHIFT - (y + 1) * zscale
    ymax = WEB_MERCATOR_TILESHIFT - y * zscale

    return [xmin, ymin, xmax, ymax]


def tile_scale(z):
    """
    Calculate tile pixel size scale for given zoom level.
    """
    TILESIZE = int(getattr(settings, 'RASTER_TILESIZE', WEB_MERCATOR_TILESIZE))
    return WEB_MERCATOR_WORLDSIZE / 2.0 ** z / TILESIZE


def closest_zoomlevel(scale, next_higher=True):
    """
    Calculate the zoom level index z that is closest to the given scale.
    The input scale needs to be provided in meters per pixel. It is then
    compared to a list of pixel sizes for all TMS zoom levels.
    """
    TILESIZE = int(getattr(settings, 'RASTER_TILESIZE', WEB_MERCATOR_TILESIZE))
    # Calculate all pixelsizes for the TMS zoom levels
    tms_pixelsizes = [WEB_MERCATOR_WORLDSIZE / (2.0 ** (i + 1) * TILESIZE) for i in range(GLOBAL_MAX_ZOOM_LEVEL)]

    # If the pixelsize is smaller than all tms sizes, default to max level
    zoomlevel = GLOBAL_MAX_ZOOM_LEVEL

    # Find zoomlevel (next-upper) for the input pixel size
    for i in range(0, GLOBAL_MAX_ZOOM_LEVEL):
        if scale - tms_pixelsizes[i] >= 0:
            zoomlevel = i
            break

    # If nextdown setting is true, adjust level
    if next_higher:
        zoomlevel += 1

    return zoomlevel
