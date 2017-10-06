from django.conf import settings
from raster.models import RasterTile
from raster.tiles.const import WEB_MERCATOR_TILESIZE
from raster.tiles.utils import tile_bounds, tile_scale


def get_raster_tile(layer_id, tilez, tilex, tiley):
    """
    Get the raster from a tile for further processing. If the requested tile
    does not exists in the database, higher level tiles are searched. If a
    higher level tile is found, it is warped to the requested zoom level. This
    ensures that a tile can be requested at any zoom level.
    """
    # Loop through zoom levels to search for a tile
    for zoom in range(tilez, -1, -1):
        # Compute multiplier to find parent raster
        multiplier = 2 ** (tilez - zoom)
        # Fetch tile
        tile = RasterTile.objects.filter(
            tilex=tilex / multiplier,
            tiley=tiley / multiplier,
            tilez=zoom,
            rasterlayer_id=layer_id,
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

                # Warp parent tile to child tile in memory.
                result = result.warp({
                    'driver': 'MEM',
                    'width': tilesize,
                    'height': tilesize,
                    'scale': [tilescale, -tilescale],
                    'origin': [bounds[0], bounds[3]],
                })

            return result
