import json

import numpy
from PIL import Image
from pyparsing import ParseException

from django.conf import settings
from django.core.exceptions import SuspiciousOperation
from django.db.models import Q
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import six
from django.views.generic import View
from raster.const import WEB_MERCATOR_TILESIZE
from raster.formulas import RasterAlgebraParser
from raster.models import Legend, RasterLayer, RasterTile
from raster.tiler import tile_bounds, tile_scale
from raster.utils import IMG_FORMATS, band_data_to_image, hex_to_rgba


class RasterView(View):

    def get_colormap(self, layer=None):
        """
        Returns colormap from request and layer, looking for a colormap in
        the request, a custom legend name to construct the legend or the
        default colormap from the layer legend.
        """
        if 'colormap' in self.request.GET:
            colormap = self.request.GET['colormap']
            colormap = json.loads(colormap)
            colormap = {k: hex_to_rgba(v) if isinstance(v, (six.string_types, int)) else v for k, v in colormap.items()}
        elif 'legend' in self.request.GET:
            legend_input = self.request.GET['legend']
            try:
                legend_input = int(legend_input)
            except ValueError:
                pass

            # Try to get legend by id, name or from input layer
            if isinstance(legend_input, int):
                legend = get_object_or_404(Legend, id=legend_input)
            else:
                legend = Legend.objects.filter(title__iexact=legend_input).first()
            colormap = legend.colormap
        elif layer:
            colormap = layer.legend.colormap
        else:
            return

        # Filter by custom entries if requested
        if 'entries' in self.request.GET:
            entries = self.request.GET['entries'].split(',')
            colormap = {k: v for (k, v) in colormap.items() if str(k) in entries}

        return colormap

    def get_format(self):
        """
        Returns image format requested.
        """
        return IMG_FORMATS[self.kwargs.get('format')]

    def write_img_to_response(self, img, stats):
        """
        Writes rgba numpy array to http response.
        """
        # Create response, and add image
        response = HttpResponse()
        frmt = self.get_format()
        response['Content-Type'] = frmt
        response['aggregation'] = json.dumps(stats)
        img.save(response, frmt)

        return response

    def get_tile(self, layer_id):
        """
        Returns a tile for rendering. If the tile does not exists, higher
        level tiles are searched and warped to lower level if found.
        """
        # Get tile indices from request
        tilex = int(self.kwargs.get('x'))
        tiley = int(self.kwargs.get('y'))
        tilez = int(self.kwargs.get('z'))

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

    def get_layer(self):
        """
        Gets layer from request data trying both name and id.
        """
        # Get layer query data from input
        if 'layer' in self.kwargs:
            data = self.kwargs.get('layer')
        elif 'layer' in self.request.GET:
            data = self.request.GET.get('layer')
        else:
            raise Http404
        # Determine query paremeter type
        try:
            data = int(data)
            query = Q(id=data)
        except ValueError:
            query = Q(rasterfile__contains='rasters/' + data)

        return get_object_or_404(RasterLayer, query)


class AlgebraView(RasterView):
    """
    A view to calculate map algebra on raster layers.
    """

    def __init__(self, *args, **kwargs):
        super(AlgebraView, self).__init__(*args, **kwargs)
        self.parser = RasterAlgebraParser()

    def get(self, request, masked=False, *args, **kwargs):
        # Get layer ids
        ids = request.GET.get('layers').split(',')

        # Parse layer ids into dictionary with variable names
        ids = {idx.split('=')[0]: idx.split('=')[1] for idx in ids}

        # Get raster data as 1D arrays and store in dict that can be used
        # for formula evaluation.
        data = {}
        for name, layerid in ids.items():
            tile = self.get_tile(layerid)
            if tile:
                data[name] = tile
            else:
                # Create empty image if any layer misses the required tile
                img = Image.new("RGBA", (WEB_MERCATOR_TILESIZE, WEB_MERCATOR_TILESIZE), (0, 0, 0, 0))
                return self.write_img_to_response(img, {})

        # Get formula from request
        formula = request.GET.get('formula')

        # Evaluate raster algebra expression, return 404 if not successful
        try:
            # Evaluate raster algebra expression
            result = self.parser.evaluate_raster_algebra(data, formula)
        except ParseException:
            raise SuspiciousOperation('Failed to evaluate raster algebra.')

        # Get array from algebra result
        result = result.bands[0].data()

        # Render tile
        colormap = self.get_colormap()
        if colormap:
            # Render tile using the legend data
            img, stats = band_data_to_image(result, colormap)
        else:
            # Scale to grayscale rgb (can be colorscheme later on)
            result = result.astype('float').ravel()
            result = 255 * (result - numpy.min(result)) / (numpy.max(result) - numpy.min(result))

            # Create rgba matrix from grayscale array
            result = numpy.array((result, result, result, numpy.repeat(255, len(result)))).T
            rgba = result.reshape(WEB_MERCATOR_TILESIZE, WEB_MERCATOR_TILESIZE, 4).astype('uint8')

            # Create image from array
            img = Image.fromarray(rgba)
            stats = {}

        # Return rendered image
        return self.write_img_to_response(img, stats)


class TmsView(RasterView):

    def get(self, *args, **kwargs):
        """
        Returns an image rendered from a raster tile.
        """
        # Get layer
        layer = self.get_layer()

        # Override color map if arg provided
        colormap = self.get_colormap(layer)

        # Get tile
        tile = self.get_tile(layer.id)

        # Render tile
        if tile and colormap:
            if kwargs.get('masked', ''):
                # Mask values
                data = numpy.ma.masked_values(
                    tile.bands[0].data(),
                    tile.bands[0].nodata_value
                )
            else:
                data = tile.bands[0].data()

            # Render tile using the legend data
            img, stats = band_data_to_image(data, colormap)
        else:
            # Create empty image if tile cant be found
            img = Image.new("RGBA", (WEB_MERCATOR_TILESIZE, WEB_MERCATOR_TILESIZE), (0, 0, 0, 0))
            stats = {}

        return self.write_img_to_response(img, stats)


class LegendView(RasterView):

    def get(self, request, legend_id):
        """
        Returns the legend for this layer as a json string. The legend is a list of
        legend entries with the attributes "name", "expression" and "color".
        """
        if(legend_id):
            # Get legend from id
            legend = get_object_or_404(Legend, id=legend_id)
        else:
            # Try to get legend from layer
            lyr = self.get_layer()
            if not lyr.legend:
                raise Http404
            legend = lyr.legend

        return HttpResponse(legend.json, content_type='application/json')
