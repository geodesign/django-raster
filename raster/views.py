import json
import numpy
import re
import string
from PIL import Image

from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpResponse, JsonResponse, Http404
from django.shortcuts import get_object_or_404
from django.views.generic import View

from .models import RasterLayer, RasterTile, Legend
from .utils import IMG_FORMATS


class AlgebraView(View):
    """
    A view to calculate map algebra on raster layers.
    """
    def get(self, request, *args, **kwargs):
        # Get layer ids
        ids = request.GET.get('layers').split(',')

        # Get tile indexes
        x, y, z = self.kwargs.get('x'), self.kwargs.get('y'), self.kwargs.get('z')

        # Get tiles
        tiles = [
            RasterTile.objects.get(
                tilex=x,
                tiley=y,
                tilez=z,
                rasterlayer_id=id
            ) for id in ids
        ]

        # Get raster data as 1D arrays and store in dict that can be used
        # for formula evaluation.
        data = {}
        for index, tile in enumerate(tiles):
            # Add tile to dict in order uising alphabetic keys
            data[string.lowercase[index]] = tile.rast.array().ravel()

        # Get formula
        formula = request.GET.get('formula')

        # Check formula validity (all vars need to be just one character long)
        if(len(re.findall('[a-z]{2}', formula))):
            raise Http404('Invalid formula, more than one character in variable name.')

        # Evaluate expression
        exec(formula, data)

        # Get result from data dict
        result = data['y']

        # Scale to grayscale rgb (can be colorscheme later on)
        result = result.astype('float')
        result = 255 * (result - numpy.min(result)) / (numpy.max(result) - numpy.min(result))

        # Create rgba matrix from grayscale array
        result = numpy.array((result, result, result, numpy.repeat(255, len(result)))).T
        rgba = result.reshape(256, 256, 4).astype('uint8')

        # Create image from array
        img = Image.fromarray(rgba)

        # Create response, add image and return
        response = HttpResponse()
        frmt = IMG_FORMATS[self.kwargs.get('format')]
        response['Content-Type'] = frmt
        img.save(response, frmt)

        return response


class TmsView(View):

    def get(self, request, *args, **kwargs):
        """
        Returns an image rendered from a raster tile.
        """
        # Get layer
        lyr = get_object_or_404(
            RasterLayer,
            rasterfile__contains='rasters/' + self.kwargs.get('layer')
        )

        # Get tile
        tile =  RasterTile.objects.filter(
            tilex=self.kwargs.get('x'),
            tiley=self.kwargs.get('y'),
            tilez=self.kwargs.get('z'),
            rasterlayer_id=lyr.id
        )

        # Override color map if arg provided
        colormap = self.get_colormap(lyr)

        # Render tile
        if tile.exists() and colormap:
            # Render tile using the legend data
            img = tile[0].rast.img(colormap)
        else:
            # Create empty image if tile cant be found
            img = Image.new("RGBA", (256, 256), (0, 0, 0, 0))

        # Create response, add image and return
        response = HttpResponse()
        response['Content-Type'] = self.get_format()
        img.save(response, self.get_format())

        return response


    def get_colormap(self, lyr):
        """
        Returns colormap from request and layer, looking for a colormap in
        the request, a custom legend name to construct the legend or the
        default colormap from the layer legend.
        """
        clmp = self.request.GET.get('colormap', None)
        if clmp:
            colormap = json.loads(clmp)
            colormap = {int(k):v for k,v in colormap.items()}
        else:
            # Get Legend, check if custom legend has been requested
            query_legend = self.request.GET.get('legend', None)
            if query_legend:
                legend = Legend.objects.filter(title__iexact=query_legend).first()
            else:
                legend = lyr.legend

            # Get colormap
            if legend:
                colormap = legend.colormap
                # Check if custom legend entries have been requested
                entries = self.request.GET.get('entries', None)
                if entries:
                    entries = entries.split(',')
                    colormap = {k:v for (k,v) in colormap.items() if str(k) in entries}
            else:
                colormap = None

        return colormap


    def get_format(self):
        """
        Returns image format requested.
        """
        return IMG_FORMATS[self.kwargs.get('format')]


def LegendView(request, layer_or_legend_name):
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
