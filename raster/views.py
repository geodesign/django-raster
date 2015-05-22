import json
import re

import numpy
from PIL import Image

from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404
from django.views.generic import View

from .models import Legend, RasterLayer, RasterTile
from .utils import IMG_FORMATS, raster_to_image


class AlgebraView(View):
    """
    A view to calculate map algebra on raster layers.
    """
    def get(self, request, *args, **kwargs):
        # Get tile indexes
        x, y, z = self.kwargs.get('x'), self.kwargs.get('y'), self.kwargs.get('z')

        # Get layer ids
        ids = request.GET.get('layers').split(',')

        # Parse layer ids into dictionary with variable names
        ids = {idx.split('=')[0]: idx.split('=')[1] for idx in ids}

        # Get raster data as 1D arrays and store in dict that can be used
        # for formula evaluation.
        data = {}
        for name, layerid in ids.items():
            tile = RasterTile.objects.filter(
                tilex=x,
                tiley=y,
                tilez=z,
                rasterlayer_id=layerid
            ).first()
            if tile:
                data[name] = tile.rast.bands[0].data().ravel()
            else:
                return self.write_rgba_to_response()

        # Get formula (allowing several parts to the formula)
        formulas = request.GET.get('formula').split(',')

        # Check formula validity (all vars need to be just one character long)
        checklist = [len(re.findall('[a-z]{2}', formula)) for formula in formulas]
        if(any(checklist)):
            raise Http404('Invalid formula, more than one character in variable name.')

        # Assure exactly one formula defines y
        checklist = ['y' in formula for formula in formulas]
        if(sum(checklist) > 1):
            raise Http404('Invalid formula, variable y found more than once.')
        elif(sum(checklist) == 0):
            raise Http404('Invalid formula, variable y not found in any formula.')

        # After formula validation, combine formulas to one expression
        formula = ';'.join(formulas)

        # Evaluate formulas, saving the formula defining y for the end
        formula_with_y = None
        for formula in formulas:
            if 'y' not in formula:
                exec(formula, data)
            else:
                formula_with_y = formula

        # Run expression with y as last formula
        exec(formula_with_y, data)

        # Get result from data dict
        result = data['y']

        # Scale to grayscale rgb (can be colorscheme later on)
        result = result.astype('float')
        result = 255 * (result - numpy.min(result)) / (numpy.max(result) - numpy.min(result))

        # Create rgba matrix from grayscale array
        result = numpy.array((result, result, result, numpy.repeat(255, len(result)))).T
        rgba = result.reshape(256, 256, 4).astype('uint8')

        return self.write_rgba_to_response(rgba)

    def get_format(self):
        """
        Returns image format requested.
        """
        return IMG_FORMATS[self.kwargs.get('format')]

    def write_rgba_to_response(self, rgba=None):
        """
        Writes rgba numpy array to http response.
        """
        if rgba is None:
            # Create empty image if no data was provided
            img = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
        else:
            # Create image from array
            img = Image.fromarray(rgba)

        # Create response, and add image
        response = HttpResponse()
        frmt = self.get_format()
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
        tile = RasterTile.objects.filter(
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
            img = raster_to_image(tile[0].rast, colormap)
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
            colormap = {int(k): v for k, v in colormap.items()}
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
                    colormap = {k: v for (k, v) in colormap.items() if str(k) in entries}
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
