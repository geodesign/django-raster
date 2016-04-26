"""
Everything required to create TMS tiles.
"""
from __future__ import unicode_literals

from django.conf import settings
from raster.models import RasterTile
from raster.tiles.const import (
    GLOBAL_MAX_ZOOM_LEVEL, QUADRANT_SIZE, WEB_MERCATOR_TILESHIFT, WEB_MERCATOR_TILESIZE, WEB_MERCATOR_WORLDSIZE
)


def get_raster_tile(layer_id, tilez, tilex, tiley):
    """
    Get the raster from a tile for further processing. If the requested tile
    does not exists in the database, higher level tiles are searched. If a
    higher level tile is found, it is warped to the requested zoom level. This
    ensures that a tile can be requested at any zoom level.
    """
    # Loop through zoom levels to search for a tile
    result = None
    for zoom in range(tilez, -1, -1):
        # Compute multiplier to find parent raster
        multiplier = 2 ** (tilez - zoom)
        # Fetch tile
        tile = RasterTile.objects.filter(
            tilex=tilex / multiplier,
            tiley=tiley / multiplier,
            tilez=zoom,
            rasterlayer_id=layer_id
        )

        if tile.exists():
            # Extract raster from tile model
            result = tile[0].rast
            # If the tile is a parent of the original, warp it to the
            # original request tile.
            if zoom < tilez:
                # Compute bounds, scale and size of child tile
                bounds = tile_bounds(tilex, tiley, tilez)
                tilesize = int(getattr(settings, 'RASTER_TILESIZE', WEB_MERCATOR_TILESIZE))
                tilescale = tile_scale(tilez)

                # Warp parent tile to child tile
                result = result.warp({
                    'width': tilesize,
                    'height': tilesize,
                    'scale': [tilescale, -tilescale],
                    'origin': [bounds[0], bounds[3]],
                })

            break

    return result


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


def quadrants(bbox, z):
    """
    Create an array of bounding boxes, representing a set of sub-regions
    defined as tile index ranges that cover the input bounding box. This
    is used to create tiles on quadrants instead of the entire file at once.
    """
    indexrange = tile_index_range(bbox, z)
    quadrant_list = []

    for tilex in range(indexrange[0], indexrange[2] + 1, QUADRANT_SIZE):
        for tiley in range(indexrange[1], indexrange[3] + 1, QUADRANT_SIZE):
            quadrant_list.append((
                tilex,
                tiley,
                min(tilex + QUADRANT_SIZE - 1, indexrange[2]),
                min(tiley + QUADRANT_SIZE - 1, indexrange[3]),
            ))

    return quadrant_list
