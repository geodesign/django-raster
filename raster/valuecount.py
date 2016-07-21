from __future__ import unicode_literals

from collections import Counter

import numpy

from django.contrib.gis.geos import MultiPolygon, Polygon
from django.core.exceptions import ObjectDoesNotExist
from raster.algebra.parser import FormulaParser, RasterAlgebraParser
from raster.exceptions import RasterAggregationException
from raster.models import Legend, RasterLayer
from raster.rasterize import rasterize
from raster.tiles.const import WEB_MERCATOR_SRID
from raster.tiles.utils import get_raster_tile, tile_index_range


class Aggregator(object):
    """
    Evaluate aggregation functions on raster layers.

    Functions such as value counts, max, min, mean or std are all values that
    depend on an entire layer, not single tiles. This class evaluates such
    functions on all tiles from a set of layers.
    """

    def __init__(self, layer_dict, formula, zoom=None, geom=None, acres=True, grouping='auto', all_touched=True):
        # Set defining parameter for this aggregator
        self.layer_dict = layer_dict
        self.formula = formula
        self.geom = geom
        self.acres = acres
        self.rastgeom = None
        self.all_touched = all_touched

        # Get layers from input dict
        self.layers = RasterLayer.objects.filter(id__in=layer_dict.values())

        # Compute zoom if not provided
        if zoom is None:
            zoom = min(self.layers.values_list('metadata__max_zoom', flat=True))
        self.zoom = zoom

        # Compute tilerange for this area and the given zoom level
        if geom:
            # Transform geom to web mercator
            if geom.srid != WEB_MERCATOR_SRID:
                geom.transform(WEB_MERCATOR_SRID)

            # Clip against max extent for limiting nr of tiles.
            # This is important for requests on large areas for small rasters.
            max_extent = MultiPolygon([Polygon.from_bbox(lyr.extent()) for lyr in self.layers]).envelope
            max_extent = geom.intersection(max_extent)

            # Abort if there is no spatial overlay
            if max_extent.empty:
                self.tilerange = None
                return
            else:
                # Compute tile index range for geometry and given zoom level
                self.tilerange = tile_index_range(max_extent.extent, zoom)
        else:
            # Get index range set for the input layers
            index_ranges = [tile_index_range(lyr.extent(), zoom) for lyr in self.layers]

            # Compute intersection of index ranges
            self.tilerange = [
                max([dat[0] for dat in index_ranges]),
                max([dat[1] for dat in index_ranges]),
                min([dat[2] for dat in index_ranges]),
                min([dat[3] for dat in index_ranges])
            ]

        # Auto determine grouping based on input data
        if grouping == 'auto':
            all_discrete = all((lyr.datatype in (RasterLayer.CATEGORICAL, RasterLayer.MASK) for lyr in self.layers))
            grouping = 'discrete' if all_discrete else 'continuous'
        elif grouping in ('discrete', 'continuous'):
            pass
        else:
            try:
                legend_id = int(grouping)
                grouping = Legend.objects.get(id=legend_id)
            except ValueError:
                pass
            except ObjectDoesNotExist:
                raise RasterAggregationException(
                    'Invalid legend ID found in grouping value for valuecount.'
                )
        self.grouping = grouping

    def tiles(self):
        """
        Generator that yields an algebra-ready data dictionary for each tile in
        the aggregator's tile range.
        """
        # Check if any tiles have been matched
        if not self.tilerange:
            return

        algebra_parser = RasterAlgebraParser()

        for tilex in range(self.tilerange[0], self.tilerange[2] + 1):
            for tiley in range(self.tilerange[1], self.tilerange[3] + 1):

                # Prepare a data dictionary with named tiles for algebra evaluation
                data = {}
                for name, layerid in self.layer_dict.items():
                    tile = get_raster_tile(layerid, self.zoom, tilex, tiley)
                    if tile:
                        data[name] = tile
                    else:
                        break

                # Ignore this tile if it is missing in any of the input layers
                if len(data) < len(self.layer_dict):
                    continue

                # Compute raster algebra
                result = algebra_parser.evaluate_raster_algebra(data, self.formula)

                # Convert band data to masked array
                result_data = numpy.ma.masked_values(
                    result.bands[0].data(),
                    result.bands[0].nodata_value,
                )

                # Apply rasterized geometry as mask if clip geometry was provided
                if self.geom:
                    result_data = self.mask_by_geom(result, result_data)

                yield result_data

    def statistics(self):
        """
        Compute statistics for this aggregator. Returns (min, max, mean, std).
        The mean and std can be computed incrementally from the number of
        obeservations t0 = sum(x^0), the sum of values t1 = sum(x^1), and the
        sum of squares t2 = sum(x^2).
        """
        # Set initial values for all variables
        t0 = t1 = t2 = 0
        max_value = min_value = None

        for data in self.tiles():
            # Apply mask to data values if mask exists
            if numpy.ma.is_masked(data):
                data = data.compressed()

            # Stop if entire data was masked
            if data.size == 0:
                continue

            # Compute incremental statistics
            t0 += data.size
            t1 += numpy.sum(data)
            t2 += numpy.sum(numpy.square(data))

            tile_max = numpy.max(data)
            tile_min = numpy.min(data)

            if max_value is None:
                max_value = tile_max
                min_value = tile_min
            else:
                max_value = max(tile_max, max_value)
                min_value = min(tile_min, min_value)

        # Compute mean and std from totals sums
        mean = t1 / t0
        std = numpy.sqrt(t0 * t2 - t1 * t1) / t0

        return (min_value, max_value, mean, std)

    def mask_by_geom(self, tile, data):
        # Rasterize the aggregation area to the result raster
        self.rastgeom = rasterize(self.geom, tile, all_touched=self.all_touched)

        # Get boolean mask based on rasterized geom
        rastgeom_mask = self.rastgeom.bands[0].data() != 1

        # Apply geometry mask to result data
        data.mask = data.mask | rastgeom_mask

        return data

    def value_count(self):
        """
        Compute aggregate statistics for a layers dictionary, potentially for
        an algebra expression and clipped by a geometry.

        The grouping parameter specifies how to group the pixel values for the
        aggregation count.

        Allowed are the following options:

        * 'auto' (the default). The output will be grouped by unique values if all
          input rasters are discrete, otherwise a numpy histogram is used.
        * 'discrete' groups the data will be grouped by unique values
        * 'continuous' groups the data in a numpy histogram
        * If an integer value is passed to the argument, it is interpreted as a
          legend_id. The data will be grouped using the legend expressions. For
          For instance, use grouping=23 for grouping the output with legend 23.
        """
        results = Counter({})

        for result_data in self.tiles():

            if self.grouping == 'discrete':
                # Compute unique counts for discrete input data
                unique_counts = numpy.unique(result_data.compressed(), return_counts=True)
                # Add counts to results
                values = dict(zip(unique_counts[0], unique_counts[1]))

            elif self.grouping == 'continuous':
                # Handle continuous case - compute histogram on masked (compressed) data
                counts, bins = numpy.histogram(result_data.compressed())

                # Create dictionary with bins as keys and histogram counts as values
                values = {}
                for i in range(len(bins) - 1):
                    values[(bins[i], bins[i + 1])] = counts[i]

            else:
                # If input is not a legend, interpret input as legend json data
                if not isinstance(self.grouping, Legend):
                    self.grouping = Legend(json=self.grouping)

                # Try getting a colormap from the input
                try:
                    colormap = self.grouping.colormap
                except:
                    raise RasterAggregationException(
                        'Invalid grouping value found for valuecount.'
                    )

                # Use colormap to compute value counts
                formula_parser = FormulaParser()
                values = {}
                for key, color in colormap.items():
                    try:
                        # Try to use the key as number directly
                        selector = result_data.compressed() == float(key)
                    except ValueError:
                        # Otherwise use it as numpy expression directly
                        selector = formula_parser.evaluate({'x': result_data.compressed()}, key)
                    values[key] = numpy.sum(selector)

            # Add counts to results
            results += Counter(values)

        # Transform pixel count to acres if requested
        scaling_factor = 1
        if self.acres and self.rastgeom and len(results):
            scaling_factor = abs(self.rastgeom.scale.x * self.rastgeom.scale.y) * 0.000247105381

        results = {
            str(int(k) if type(k) == numpy.float64 and int(k) == k else k):
            v * scaling_factor for k, v in results.items()
        }

        return results
