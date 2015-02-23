import json
from PIL import Image

from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpResponse, JsonResponse, Http404
from django.shortcuts import get_object_or_404

from raster.models import RasterLayer, RasterTile, Legend

from utils import IMG_FORMATS


def tms(request, layer, x, y, z, format):
    """
    A TMS Endpoint for Raster Tiles that were parsed with XYZ indices.
    """
    # Get layer
    lyr = get_object_or_404(RasterLayer, rasterfile__contains='rasters/' + layer)

    # Get tile
    tile =  RasterTile.objects.filter(
            tilex=x,
            tiley=y,
            tilez=z,
            rasterlayer_id=lyr.id)

    # Get Legend, check if custom legend has been requested
    query_legend = request.GET.get('legend', None)
    if query_legend:
        legend = Legend.objects.filter(title__iexact=query_legend).first()
    else:
        legend = lyr.legend

    # Get colormap
    if legend:
        colormap = legend.colormap
        # Check if custom legend entries have been requested
        entries = request.GET.get('entries', None)
        if entries:
            entries = entries.split(',')
            colormap = {k:v for (k,v) in colormap.items() if str(k) in entries}
    else:
        colormap = None

    # Render tile
    if tile.exists() and colormap:
        # Render tile using the legend data
        img = tile[0].rast.img(colormap)
    else:
        # Create empty image if tile cant be found
        img = Image.new("RGBA", (256, 256), (0, 0, 0, 0))

    # Create response, add image and return
    response = HttpResponse()    
    response['Content-Type'] = IMG_FORMATS[format]
    img.save(response, IMG_FORMATS[format])

    return response

def legend(request, layer_or_legend_name):
    """
    Returns the legend for this layer as a json string. The legend is a list of
    legend entries with the attributes "name", "expression" and "color".
    """
    try:
        lyr = RasterLayer.objects.get(rasterfile__contains='rasters/' + layer_or_legend_name)
        if lyr.legend:
            legend = lyr.legend
    except RasterLayer.DoesNotExist:
        try:
            legend = Legend.objects.get(title__iexact=layer_or_legend_name)
        except Legend.DoesNotExist:
            raise Http404()

    return HttpResponse(legend.json, content_type='application/json')
