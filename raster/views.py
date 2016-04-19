import json
import zipfile
from datetime import datetime
from tempfile import NamedTemporaryFile

import numpy
from PIL import Image

from django.conf import settings
from django.contrib.gis.gdal import GDALRaster
from django.contrib.gis.geos import Polygon
from django.db.models import Q
from django.http import FileResponse, Http404, HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import six
from django.views.generic import View
from raster.algebra.const import ALGEBRA_PIXEL_TYPE_GDAL
from raster.algebra.parser import RasterAlgebraParser
from raster.const import EXPORT_MAX_PIXELS, IMG_FORMATS
from raster.exceptions import RasterAlgebraException
from raster.models import Legend, RasterLayer
from raster.tiles.const import WEB_MERCATOR_SRID, WEB_MERCATOR_TILESIZE
from raster.tiles.utils import get_raster_tile, tile_bounds, tile_index_range, tile_scale
from raster.utils import band_data_to_image, hex_to_rgba


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
        elif layer and hasattr(layer.legend, 'colormap'):
            colormap = layer.legend.colormap
        elif layer:
            # Construct a grayscale colormap from layer metadata
            meta = layer.rasterlayerbandmetadata_set.first()

            # Return if no metadata can be found to construct the colormap
            if meta is None:
                return

            # Set the number of breaks to be used
            nr_of_breaks = 7

            # Compute bin width for a linear scaling
            diff = (meta.max - meta.min) / 7

            # Create colormap with seven breaks
            colormap = {}
            for i in range(nr_of_breaks):
                if i == 0:
                    expression = '({0} <= x) & (x <= {1})'
                else:
                    expression = '({0} < x) & (x <= {1})'
                expression = expression.format(meta.min + diff * i, meta.min + diff * (i + 1))
                colormap[expression] = [(255 / (nr_of_breaks - 1)) * i] * 3 + [255, ]
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
        tilez = int(self.kwargs.get('z'))
        tilex = int(self.kwargs.get('x'))
        tiley = int(self.kwargs.get('y'))

        return get_raster_tile(layer_id, tilez, tilex, tiley)

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

    def get_ids(self):
        # Get layer ids
        ids = self.request.GET.get('layers', '').split(',')

        # Check if layer parameter is valid
        if not len(ids) or not all('=' in idx for idx in ids):
            raise RasterAlgebraException('Layer parameter is not valid.')

        # Split id/name input pairs
        ids = [idx.split('=') for idx in ids]

        # Convert ids to integer
        try:
            ids = {idx[0]: int(idx[1]) for idx in ids}
        except ValueError:
            raise RasterAlgebraException('Layer parameter is not valid.')

        return ids

    def get(self, request, *args, **kwargs):
        parser = RasterAlgebraParser()

        # Get layer ids
        ids = self.get_ids()

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

        # Evaluate raster algebra expression, return 400 if not successful
        try:
            # Evaluate raster algebra expression
            result = parser.evaluate_raster_algebra(data, formula)
        except:
            raise RasterAlgebraException('Failed to evaluate raster algebra.')

        # Get array from algebra result
        result = numpy.ma.masked_values(
            result.bands[0].data(),
            result.bands[0].nodata_value,
        )

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
            data = numpy.ma.masked_values(
                tile.bands[0].data(),
                tile.bands[0].nodata_value,
            )
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


class ExportView(AlgebraView):

    def construct_raster(self, z, xmin, xmax, ymin, ymax):
        bounds = []
        for x in range(xmin, xmax + 1):
            for y in range(ymin, ymax + 1):
                bounds.append(tile_bounds(x, y, z))
        bounds = [
            min([bnd[0] for bnd in bounds]),
            min([bnd[1] for bnd in bounds]),
            max([bnd[2] for bnd in bounds]),
            max([bnd[3] for bnd in bounds]),
        ]
        scale = tile_scale(z)
        raster_workdir = getattr(settings, 'RASTER_WORKDIR', None)
        self.exportfile = NamedTemporaryFile(dir=raster_workdir, suffix='.tif')
        return GDALRaster({
            'srid': WEB_MERCATOR_SRID,
            'width': (xmax - xmin + 1) * WEB_MERCATOR_TILESIZE,
            'height': (ymax - ymin + 1) * WEB_MERCATOR_TILESIZE,
            'scale': (scale, -scale),
            'origin': (bounds[0], bounds[3]),
            'driver': 'tif',
            'bands': [{'data': [0], 'nodata_value': 0}],
            'name': self.exportfile.name,
            'datatype': ALGEBRA_PIXEL_TYPE_GDAL,
        })

    def get_tile_range(self):
        # Get raster layers
        layers = RasterLayer.objects.filter(id__in=self.get_ids().values())
        # Establish zoom level
        if self.request.GET.get('zoom', None):
            zlevel = int(self.request.GET.get('zoom'))
        else:
            # Get highest zoom level of all input layers
            zlevel = max([layer.metadata.max_zoom for layer in layers])
        # Use bounding box to compute tile range
        if self.request.GET.get('bbox', None):
            bbox = Polygon.from_bbox(self.request.GET.get('bbox').split(','))
            bbox.srid = 4326
            bbox.transform(WEB_MERCATOR_SRID)
            tile_range = tile_index_range(bbox.extent, zlevel)
        else:
            # Get list of tile ranges
            layer_ranges = []
            for layer in layers:
                layer_ranges.append(tile_index_range(layer.extent(), zlevel))
            # Estabish overlap of tile index ranges
            tile_range = [
                min([rng[0] for rng in layer_ranges]),
                min([rng[1] for rng in layer_ranges]),
                max([rng[2] for rng in layer_ranges]),
                max([rng[3] for rng in layer_ranges]),
            ]
        return [zlevel, ] + tile_range

    def get(self, request):
        parser = RasterAlgebraParser()
        # Get formula from request
        formula = request.GET.get('formula')
        # Get id list from request
        ids = self.get_ids()
        zoom, xmin, ymin, xmax, ymax = self.get_tile_range()
        if WEB_MERCATOR_TILESIZE * (xmax - xmin) * WEB_MERCATOR_TILESIZE * (ymax - ymin) > EXPORT_MAX_PIXELS:
            raise RasterAlgebraException('Export raster too large.')
        # Construct an empty raster with the output dimensions
        result_raster = self.construct_raster(zoom, xmin, xmax, ymin, ymax)
        target = result_raster.bands[0]
        # Get raster data as 1D arrays and store in dict that can be used
        # for formula evaluation.
        for xindex, x in enumerate(range(xmin, xmax + 1)):
            for yindex, y in enumerate(range(ymin, ymax + 1)):
                data = {}
                for name, layerid in ids.items():
                    tile = get_raster_tile(layerid, zoom, x, y)
                    if tile:
                        data[name] = tile
                # Ignore this tile if data is not found for all layers
                if len(data) != len(ids):
                    continue
                # Evaluate raster algebra expression, return 400 if not successful
                try:
                    # Evaluate raster algebra expression
                    tile_result = parser.evaluate_raster_algebra(data, formula)
                except:
                    raise RasterAlgebraException('Failed to evaluate raster algebra.')
                # Update nodata value on target
                target.nodata_value = tile_result.bands[0].nodata_value
                # Update results raster with algebra
                target.data(
                    data=tile_result.bands[0].data(),
                    size=(WEB_MERCATOR_TILESIZE, WEB_MERCATOR_TILESIZE),
                    offset=(xindex * WEB_MERCATOR_TILESIZE, yindex * WEB_MERCATOR_TILESIZE),
                )
        # Create filename base with datetime stamp
        filename_base = 'algebra_export_{0}'.format(datetime.now().strftime('%Y_%m_%d_%H_%M'))
        # Compress resulting raster file into a zip archive
        raster_workdir = getattr(settings, 'RASTER_WORKDIR', None)
        dest = NamedTemporaryFile(dir=raster_workdir, suffix='.zip')
        dest_zip = zipfile.ZipFile(dest.name, 'w', allowZip64=True)
        dest_zip.write(
            filename=self.exportfile.name,
            arcname=filename_base + '.tif',
            compress_type=zipfile.ZIP_DEFLATED,
        )
        dest_zip.close()
        # Create file based response containing zip file and return for download
        response = FileResponse(
            open(dest.name, 'rb'),
            content_type='application/zip'
        )
        response['Content-Disposition'] = 'attachment; filename="{0}"'.format(filename_base + '.zip')
        return response
