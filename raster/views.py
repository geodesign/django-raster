from __future__ import unicode_literals

import json
import os
import re
import uuid
import zipfile
from datetime import datetime
from tempfile import NamedTemporaryFile

import numpy
from PIL import Image

from django.conf import settings
from django.contrib.gis.gdal import GDALRaster
from django.contrib.gis.gdal.raster.const import VSI_FILESYSTEM_BASEPATH
from django.contrib.gis.geos import Polygon
from django.db.models import Max, Q
from django.http import FileResponse, Http404, HttpResponse
from django.shortcuts import get_object_or_404
from django.template.defaultfilters import slugify
from django.utils.functional import cached_property
from django.views.generic import View
from raster.algebra.const import ALGEBRA_PIXEL_TYPE_GDAL, BAND_INDEX_SEPARATOR
from raster.algebra.parser import RasterAlgebraParser
from raster.const import EXPORT_MAX_PIXELS, IMG_ENHANCEMENTS, IMG_FORMATS, MAX_EXPORT_NAME_LENGTH, README_TEMPLATE
from raster.exceptions import RasterAlgebraException
from raster.models import Legend, RasterLayer, RasterLayerBandMetadata, RasterLayerMetadata
from raster.shortcuts import get_session_colormap
from raster.tiles.const import WEB_MERCATOR_SRID, WEB_MERCATOR_TILESIZE
from raster.tiles.lookup import get_raster_tile
from raster.tiles.utils import tile_bounds, tile_index_range, tile_scale
from raster.utils import band_data_to_image, colormap_to_rgba, pixel_value_from_point


class RasterView(View):

    @property
    def is_pixel_request(self):
        return 'xcoord' in self.kwargs

    def get_colormap(self, layer=None):
        """
        Returns colormap from request and layer, looking for a colormap in the
        request or session, a custom legend name to construct the legend or the
        default colormap from the layer legend.
        """
        colormap = None

        if 'colormap' in self.request.GET:
            colormap = colormap_to_rgba(json.loads(self.request.GET['colormap']))
            # Ensure colormap range is in float format.
            if 'range' in colormap:
                colormap['range'] = (float(colormap['range'][0]), float(colormap['range'][1]))
        elif 'legend' in self.request.GET:
            store = self.request.GET.get('store', 'database')
            if store == 'session':
                colormap = get_session_colormap(
                    self.request.session,
                    self.request.GET['legend']
                )
            else:
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

        elif 'layer' in self.kwargs:
            # Get legend for the input layer.
            legend = Legend.objects.filter(rasterlayer=self.kwargs.get('layer')).first()

            if legend and hasattr(legend, 'colormap'):
                colormap = legend.colormap

        if not colormap:
            # Use a continous grayscale color scheme.
            colormap = {
                'continuous': True,
                'from': (0, 0, 0),
                'to': (255, 255, 255),
            }
        else:
            # Add layer level value range to continuous colormaps if it was
            # not provided manually.
            if 'continuous' in colormap and 'range' not in colormap:
                meta = RasterLayerBandMetadata.objects.filter(rasterlayer_id=self.kwargs.get('layer')).first()
                if meta:
                    colormap['range'] = (meta.min, meta.max)

            # Filter by custom entries if requested
            if colormap and 'entries' in self.request.GET:
                entries = self.request.GET['entries'].split(',')
                colormap = {k: v for (k, v) in colormap.items() if str(k) in entries}

        return colormap

    def get_format(self):
        """
        Returns image format requested.
        """
        return IMG_FORMATS[self.kwargs.get('frmt')]

    def enhance(self, img):
        for key, enhancer in IMG_ENHANCEMENTS.items():
            if key in self.request.GET:
                img = enhancer(img).enhance(float(self.request.GET.get(key)))
        return img

    def write_img_to_response(self, img, stats):
        """
        Writes rgba numpy array to http response.
        """
        # Create response.
        response = HttpResponse()
        frmt, content_type = self.get_format()
        response['Content-Type'] = content_type
        response['aggregation'] = json.dumps(stats)
        # Enhance image if requested.
        img = self.enhance(img)
        # Save image to response.
        img.save(response, frmt)

        return response

    def get_tile(self, layer_id, zlevel=None):
        """
        Returns a tile for rendering. If the tile does not exists, higher
        level tiles are searched and warped to lower level if found.
        """
        if self.is_pixel_request:
            tilez = self.max_zoom
            # Derive the tile index from the input coordinates.
            xcoord = float(self.kwargs.get('xcoord'))
            ycoord = float(self.kwargs.get('ycoord'))
            bbox = [xcoord, ycoord, xcoord, ycoord]
            indexrange = tile_index_range(bbox, tilez)
            tilex = indexrange[0]
            tiley = indexrange[1]
        else:
            # Get tile indices from the request url parameters.
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

    @cached_property
    def max_zoom(self):
        return RasterLayerMetadata.objects.filter(
            rasterlayer_id__in=self.get_ids().values()
        ).aggregate(zlevel=Max('max_zoom'))['zlevel']


class AlgebraView(RasterView):
    """
    A view to calculate map algebra on raster layers.
    """

    _layer_ids = None

    def get_ids(self):
        if self._layer_ids is not None:
            return self._layer_ids

        if 'layer' in self.kwargs:
            # For tms requests, construct simple ids dictionary.
            data = self.kwargs.get('layer')
            # Determine query paremeter type
            try:
                layer_id = int(data)
            except ValueError:
                query = Q(rasterfile__contains='rasters/' + data)
                layer_id = get_object_or_404(RasterLayer, query).id
            # For TMS tile request, get the layer id from the url.
            self._layer_ids = {'x': layer_id}
        else:
            # For algebra requests, get the layer ids from the query parameter.
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
            self._layer_ids = ids

        return self._layer_ids

    def get(self, request, *args, **kwargs):
        # Get layer ids
        ids = self.get_ids()

        # Prepare unique list of layer ids to be efficient if the same layer
        # is used multiple times (for band access for instance).
        layerids = set(ids.values())

        # Get the tiles for each unique layer.
        tiles = {}
        for layerid in layerids:
            tile = self.get_tile(layerid)
            if tile:
                tiles[layerid] = tile
            else:
                # Create empty image if any layer misses the required tile
                img = Image.new("RGBA", (WEB_MERCATOR_TILESIZE, WEB_MERCATOR_TILESIZE), (0, 0, 0, 0))
                return self.write_img_to_response(img, {})

        # Map tiles to a dict with formula names as keys.
        data = {}
        for name, layerid in ids.items():
            data[name] = tiles[layerid]

        # Get formula from request
        if 'layer' in self.kwargs:
            # Set the formula to trivial for TMS requests.
            formula = 'x'
        else:
            formula = request.GET.get('formula', None)

        # Dispatch by request type. If a formula was provided, use raster
        # algebra otherwise look for rgb request.
        if formula:
            return self.get_algebra(data, formula)
        else:
            keys = [key.split(BAND_INDEX_SEPARATOR)[0] for key in data.keys()]
            if 'r' in keys and 'g' in keys and 'b' in keys:
                return self.get_rgb(data)
            else:
                raise RasterAlgebraException(
                    'Specify raster algebra formula or provide rgb layer keys.'
                )

    def get_algebra(self, data, formula):
        parser = RasterAlgebraParser()

        # Evaluate raster algebra expression, return 400 if not successful
        try:
            # Evaluate raster algebra expression
            result = parser.evaluate_raster_algebra(data, formula)
        except:
            raise RasterAlgebraException('Failed to evaluate raster algebra.')

        # For pixel value requests, return result as json.
        if self.is_pixel_request:
            xcoord = float(self.kwargs.get('xcoord'))
            ycoord = float(self.kwargs.get('ycoord'))
            val = pixel_value_from_point(result, [xcoord, ycoord])
            return HttpResponse(
                json.dumps({'x': xcoord, 'y': ycoord, 'value': val}),
                content_type='application/json',
            )

        # For tif requests, skip colormap and return georeferenced tif file.
        if self.kwargs.get('frmt') == 'tif':
            vsi_path = os.path.join(VSI_FILESYSTEM_BASEPATH, str(uuid.uuid4()))
            rast = result.warp({
                'name': vsi_path,
                'driver': 'tif',
                'compress': 'DEFLATE',
            })
            content_type = IMG_FORMATS['tif'][1]
            return HttpResponse(rast.vsi_buffer, content_type)

        # Get array from algebra result
        if result.bands[0].nodata_value is None:
            result = result.bands[0].data()
        else:
            result = numpy.ma.masked_values(
                result.bands[0].data(),
                result.bands[0].nodata_value,
            )

        # Get colormap.
        colormap = self.get_colormap()

        # Render tile using the legend data
        img, stats = band_data_to_image(result, colormap)

        # Return rendered image
        return self.write_img_to_response(img, stats)

    def get_rgb(self, data):
        # Get data arrays from tiles, by band if requested.
        for key, tile in data.items():

            keysplit = key.split(BAND_INDEX_SEPARATOR)
            variable = keysplit[0]

            if len(keysplit) > 1:
                band_index = int(keysplit[1])
            else:
                band_index = 0

            if variable == 'r':
                red = tile.bands[band_index].data()
            elif variable == 'g':
                green = tile.bands[band_index].data()
            elif variable == 'b':
                blue = tile.bands[band_index].data()

        # Get scale for the image value range.
        if 'scale' in self.request.GET:
            # The scale is either a number or two numbers separated by comma.
            scale = self.request.GET.get('scale').split(',')
            if len(scale) == 1:
                scale_min = 0
                scale_max = float(scale[0])
            else:
                # Get min an max scale from
                scale_min = float(scale[0])
                scale_max = float(scale[1])

                # Clip the image minimum.
                red[red < scale_min] = scale_min
                green[green < scale_min] = scale_min
                blue[blue < scale_min] = scale_min

            # Clip the image maximum.
            red[red > scale_max] = scale_max
            green[green > scale_max] = scale_max
            blue[blue > scale_max] = scale_max

            # Scale the image.
            red = 255 * (red - scale_min) / scale_max
            green = 255 * (green - scale_min) / scale_max
            blue = 255 * (blue - scale_min) / scale_max

        if 'alpha' in self.request.GET:
            mode = 'RGBA'
            reshape = 4
            # Create the alpha channel.
            alpha = 255 * (red > 0) * (blue > 0) * (green > 0)
            img_array = numpy.array((red.ravel(), green.ravel(), blue.ravel(), alpha.ravel()))
        else:
            mode = 'RGB'
            reshape = 3
            img_array = numpy.array((red.ravel(), green.ravel(), blue.ravel()))

        # Reshape array into tile size.
        img_array = img_array.T.reshape(WEB_MERCATOR_TILESIZE, WEB_MERCATOR_TILESIZE, reshape).astype('uint8')

        # Create image from array
        img = Image.fromarray(img_array, mode=mode)
        stats = {}

        # Return rendered image
        return self.write_img_to_response(img, stats)


class LegendView(RasterView):

    def get(self, request, legend_id):
        """
        Returns the legend for this layer as a json string. The legend is a list of
        legend entries with the attributes "name", "expression" and "color".
        """
        if legend_id:
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
        """
        Create an empty tif raster file on disk using the input tile range. The
        new raster aligns with the xyz tile scheme and can be filled
        sequentially with raster algebra results.
        """
        # Compute bounds and scale to construct raster.
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
        # Create tempfile.
        raster_workdir = getattr(settings, 'RASTER_WORKDIR', None)
        self.exportfile = NamedTemporaryFile(dir=raster_workdir, suffix='.tif')
        # Instantiate raster using the tempfile path.
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
        """
        Compute a xyz tile range from the query parameters. If no bbox
        parameter is found, the range defaults to the maximum extent of
        all input raster layers.
        """
        # Get raster layers
        layers = RasterLayer.objects.filter(id__in=self.get_ids().values())
        # Establish zoom level
        if self.request.GET.get('zoom', None):
            zlevel = int(self.request.GET.get('zoom'))
        else:
            # Get highest zoom level of all input layers
            zlevel = self.max_zoom
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

    def write_colormap(self, zfile):
        # Try to get colormap
        colormap = self.get_colormap()
        # Set a simple header for this colormap
        colorstr = '# Raster Algebra Colormap\n'
        # Check if this is a continuous legend.
        colorstr += 'INTERPOLATION: ' + ('CONTINUOUS' if colormap.pop('continuous', None) else 'DISCRETE') + '\n'
        # Add expressions and colors of the colormap
        for key, val in colormap.items():
            colorstr += str(key) + ',' + ','.join((str(x) for x in val)) + ',' + str(key) + '\n'
        # Write colormap file
        zfile.writestr('COLORMAP.txt', colorstr)

    def write_readme(self, zfile):
        # Get tile index range
        zoom, xmin, ymin, xmax, ymax = self.get_tile_range()
        # Construct layer names string
        layerstr = ''
        for name, layerid in self.get_ids().items():
            layer = RasterLayer.objects.get(id=layerid)
            layerstr += '{layerid} "{name}" (Formula label: {label})\n'.format(
                name=layer.name,
                label=name,
                layerid=layerid
            )
        # Get description, append newline if provided
        description = self.request.GET.get('description', '')
        if description:
            description += '\n'
        # Initiate metadata object
        readmedata = {
            'datetime': datetime.now().strftime('%Y-%m-%d at %H:%M'),
            'url': self.request.build_absolute_uri(),
            'bbox': self.request.GET.get('bbox', 'Minimum bounding-box covering all layers.'),
            'formula': self.request.GET.get('formula'),
            'zoom': str(zoom),
            'xindexrange': '{} - {}'.format(xmin, xmax),
            'yindexrange': '{} - {}'.format(ymin, ymax),
            'layers': layerstr,
            'description': description,
        }
        # Write readme file
        readme = README_TEMPLATE.format(**readmedata)
        zfile.writestr('README.txt', readme)

    def get(self, request):
        # Initiate algebra parser
        parser = RasterAlgebraParser()
        # Get formula from request
        formula = request.GET.get('formula')
        # Get id list from request
        ids = self.get_ids()
        # Compute tile index range
        zoom, xmin, ymin, xmax, ymax = self.get_tile_range()
        # Check maximum size of target raster in pixels
        max_pixels = getattr(settings, 'RASTER_EXPORT_MAX_PIXELS', EXPORT_MAX_PIXELS)
        if WEB_MERCATOR_TILESIZE * (xmax - xmin) * WEB_MERCATOR_TILESIZE * (ymax - ymin) > max_pixels:
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
        filename_base = 'algebra_export'
        # Add name slug to filename if provided
        if request.GET.get('filename', ''):
            # Sluggify name
            slug = slugify(request.GET.get('filename'))
            # Remove all unwanted characters
            slug = "".join([c for c in slug if re.match(r'\w|\-', c)])
            # Limit length of custom name slug
            slug = slug[:MAX_EXPORT_NAME_LENGTH]
            # Add name slug to filename base
            filename_base += '_' + slug
        filename_base += '_{0}'.format(datetime.now().strftime('%Y_%m_%d_%H_%M'))
        # Compress resulting raster file into a zip archive
        raster_workdir = getattr(settings, 'RASTER_WORKDIR', None)
        dest = NamedTemporaryFile(dir=raster_workdir, suffix='.zip')
        dest_zip = zipfile.ZipFile(dest.name, 'w', allowZip64=True)
        dest_zip.write(
            filename=self.exportfile.name,
            arcname=filename_base + '.tif',
            compress_type=zipfile.ZIP_DEFLATED,
        )
        # Write README.txt and COLORMAP.txt files to zip file
        self.write_readme(dest_zip)
        self.write_colormap(dest_zip)
        # Close zip file before returning
        dest_zip.close()
        # Create file based response containing zip file and return for download
        response = FileResponse(
            open(dest.name, 'rb'),
            content_type='application/zip'
        )
        response['Content-Disposition'] = 'attachment; filename="{0}"'.format(filename_base + '.zip')
        return response
