from collections import Counter

import numpy

from django.contrib.gis.geos import GEOSGeometry, MultiPolygon, Polygon
from django.db import connection

from .const import WEB_MERCATOR_SRID
from .formulas import RasterAlgebraParser
from .rasterize import rasterize
from .tiler import tile_index_range


CLIPPED_VALUE_COUNT_SQL = """
WITH tiles_for_agg AS (
    SELECT ST_ValueCount(ST_Clip(ST_Transform(rast, {geom_srid}), ST_GeomFromEWKT('{geom_ewkt}'))) AS vcresult
    FROM raster_rastertile
    WHERE ST_Intersects(rast, ST_Transform(ST_GeomFromEWKT('{geom_ewkt}'), {rast_srid}))
    AND rasterlayer_id = {rasterlayer_id}
    AND tilez = {zoom}
)
SELECT (vcresult).value, SUM((vcresult).count) AS count
FROM tiles_for_agg
GROUP BY (vcresult).value
"""

GLOBAL_VALUE_COUNT_SQL = """
WITH tiles_for_agg AS (
    SELECT ST_ValueCount(rast) AS vcresult
    FROM raster_rastertile
    WHERE rasterlayer_id = {rasterlayer_id}
    AND tilez = {zoom}
)
SELECT (vcresult).value, SUM((vcresult).count) AS count
FROM tiles_for_agg
GROUP BY (vcresult).value
"""

MINSIZE_SQL = """
SELECT
    ST_ScaleX(ST_Transform(rast, {srid})) AS scalex,
    ST_ScaleY(ST_Transform(rast, {srid})) AS scaley
FROM raster_rastertile
WHERE rasterlayer_id = {rasterlayer_id}
AND tilez = {zoom}
LIMIT 1
"""

MAX_ZOOM_SQL = """
SELECT MAX(tilez)
FROM raster_rastertile
WHERE rasterlayer_id={rasterlayer_id}
"""


def aggregator(layer_dict, zoom, geom=None, formula=None, acres=True):
    """
    Compute aggregate statistics for a layers dictionary, potentially for
    an algebra expression and clipped by a geometry.
    """
    from .models import RasterLayer, RasterTile

    parser = RasterAlgebraParser()

    # Get layers
    layers = RasterLayer.objects.filter(id__in=layer_dict.values())

    # Compute tilerange for this area and the given zoom level
    if geom:
        # Transform geom to web mercator
        if geom.srid != WEB_MERCATOR_SRID:
            geom.transform(WEB_MERCATOR_SRID)

        # Clip against max extent for limiting nr of tiles.
        # This is important for requests on large areas for small rasters.
        max_extent = MultiPolygon([Polygon.from_bbox(lyr.extent()) for lyr in layers]).envelope
        max_extent = geom.intersection(max_extent)

        # Compute tile index range for geometry and given zoom level
        tilerange = tile_index_range(max_extent.extent, zoom)
    else:
        # Get index range set for the input layers
        index_ranges = [lyr.index_range(zoom) for lyr in layers]

        # Compute intersection of index ranges
        tilerange = [
            max([dat['tilex__min'] for dat in index_ranges]),
            max([dat['tiley__min'] for dat in index_ranges]),
            min([dat['tilex__max'] for dat in index_ranges]),
            min([dat['tiley__max'] for dat in index_ranges])
        ]

    # Check if all input layers are discrete
    all_discrete = all([lyr.datatype in ['ca', 'ma'] for lyr in layers])

    # Loop through tiles and evaluate raster algebra for each tile
    results = Counter({})
    rastgeom = None
    for tilex in range(tilerange[0], tilerange[2] + 1):
        for tiley in range(tilerange[1], tilerange[3] + 1):
            # Prepare a data dictionary with named tiles for algebra evaluation
            data = {}
            for name, layerid in layer_dict.items():
                tile = RasterTile.objects.filter(
                    tilex=tilex,
                    tiley=tiley,
                    tilez=zoom,
                    rasterlayer_id=layerid
                ).first()
                if tile:
                    data[name] = tile.rast
                else:
                    # Ignore this tile if any layer has no data for it
                    break

            if data != {}:
                # Evaluate algebra on tiles
                result = parser.evaluate_raster_algebra(data, formula)

                # Get resulting array masked with na values
                result_data = numpy.ma.masked_values(result.bands[0].data(), result.bands[0].nodata_value)

                # Apply rasterized geometry as mask if clip geometry was provided
                if geom:
                    # Rasterize the aggregation area to the result raster
                    rastgeom = rasterize(geom, result)

                    # Get boolean mask based on rasterized geom
                    rastgeom_mask = rastgeom.bands[0].data() != 1

                    # Apply geometry mask to result data
                    result_data.mask = result_data.mask | rastgeom_mask

                # Compute unique counts for discrete input data
                if all_discrete:
                    unique_counts = numpy.unique(result_data, return_counts=True)
                    # Add counts to results
                    results += Counter(dict(zip(unique_counts[0], unique_counts[1])))
                else:
                    # Handle continuous case - compute histogram
                    counts, bins = numpy.histogram(result_data)

                    # Create dictionary with bins as keys and histogram counts as values
                    values = {}
                    for i in range(len(bins) - 1):
                        values[(bins[i], bins[i + 1])] = counts[i]

                    # Add counts to results
                    results += Counter(values)

    # Transform pixel count to acres if requested
    scaling_factor = 1
    if acres and rastgeom and len(results):
        scaling_factor = abs(rastgeom.scale.x * rastgeom.scale.y) * 0.000247105381
    results = {
        str(int(k) if type(k) == numpy.float64 and int(k) == k else k):
        v * scaling_factor for k, v in results.iteritems()
    }

    return results


class ValueCountMixin(object):
    """
    Value count methods for Raster Layers.
    """
    def db_value_count(self, geom=None, area=False, zoom=None):
        """
        Compute value count in database.
        """
        if not zoom:
            zoom = self._max_zoom

        # Check that raster is categorical or mask
        if self.datatype not in ['ca', 'ma']:
            raise TypeError(
                'Wrong rastertype, value counts can only be '
                'calculated for categorical or mask raster tpyes'
            )

        if geom:
            # Make sure geometry is GEOS Geom
            geom = GEOSGeometry(geom)

            sql = CLIPPED_VALUE_COUNT_SQL.format(
                geom_ewkt=geom.ewkt,
                geom_srid=geom.srid,
                rast_srid=WEB_MERCATOR_SRID,
                rasterlayer_id=self.id,
                zoom=zoom
            )
        else:
            sql = GLOBAL_VALUE_COUNT_SQL.format(
                rasterlayer_id=self.id,
                zoom=zoom
            )

        cursor = connection.cursor()
        cursor.execute(sql)

        # Convert value count to areas if requested
        if area:
            scalex, scaley = self._min_pixelsize(geom.srid)
            return {int(row[0]): int(row[1]) * scalex * scaley for row in cursor.fetchall()}
        else:
            return {int(row[0]): int(row[1]) for row in cursor.fetchall()}

    _maxz = None

    @property
    def _max_zoom(self):
        """
        Get max zoom for this layer.
        """
        if not self._maxz:
            cursor = connection.cursor()
            cursor.execute(MAX_ZOOM_SQL.format(rasterlayer_id=self.id))
            self._maxz = cursor.fetchone()[0]
        return self._maxz

    def pixelsize(self, srid=WEB_MERCATOR_SRID, zoom=None):
        """
        Compute size of a pixel for a given srid and zoomlevel.
        """
        if not zoom:
            zoom = self._max_zoom

        sql = MINSIZE_SQL.format(
            srid=srid,
            rasterlayer_id=self.id,
            zoom=zoom
        )

        cursor = connection.cursor()
        cursor.execute(sql)
        res = cursor.fetchone()
        self._minsize = (abs(res[0]), abs(res[1]))
        self._minsize_srid = srid

        return self._minsize

    def value_count(self, geom=None, area=False, zoom=None):
        """
        Compute value counts or histograms for rasterlayers within a geometry.
        """
        # Automatically determine zoom if not provided
        if not zoom:
            zoom = self._max_zoom

        # Setup layer id and formula for evaluation of aggregator
        ids = {'a': self.id}
        formula = 'a'

        return aggregator(ids, zoom, geom, formula, acres=area)
