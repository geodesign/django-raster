import json
from PIL import Image

from django.http import HttpResponse
from django.shortcuts import get_object_or_404

from raster.models import RasterLayer, RasterTile

from utils import IMG_FORMATS


def tms(request, layers, x, y, z, format):
    """
    A TMS Endpoint for Raster Tiles that were parsed with XYZ indices.
    """
    # Get layer
    lyr = get_object_or_404(RasterLayer, rasterfile__contains='rasters/' + layers)

    # Get tile
    tile =  RasterTile.objects.filter(
            tilex=x,
            tiley=y,
            tilez=z,
            rasterlayer_id=lyr.id)

    if tile.exists() and lyr.legend:
        # Render tile using the legend data
        img = tile[0].rast.img(lyr.legend.colormap)
    else:
        # Create empty image if tile cant be found
        img = Image.new("RGBA", (256, 256), (0, 0, 0, 0))


    # Create response, add image and return
    response = HttpResponse()    
    response['Content-Type'] = IMG_FORMATS[format]
    img.save(response, IMG_FORMATS[format])

    return response
