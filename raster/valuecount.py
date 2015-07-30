import numpy

from django.contrib.gis.geos import GEOSGeometry
from django.db import connection
from raster.const import WEB_MERCATOR_SRID
from raster.rasterize import rasterize


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

        # Get raster tiles
        if geom:
            if geom.srid != WEB_MERCATOR_SRID:
                geom.transform(WEB_MERCATOR_SRID)

            # Filter tiles by geometry intersection
            tiles = self.rastertile_set.raw(
                "SELECT * FROM raster_rastertile "
                "WHERE ST_Intersects(rast, ST_GeomFromEWKT('{geom_ewkt}')) "
                "AND tilez={zoom} "
                "AND rasterlayer_id={rstid}"
                .format(geom_ewkt=geom.ewkt, zoom=zoom, rstid=self.id)
            )
            rastgeom = rasterize(geom, tiles[0].rast)
            tile_data = [tile.rast.bands[0].data()[rastgeom.bands[0].data() == 1] for tile in tiles]
        else:
            tiles = self.rastertile_set.filter(tilez=zoom)
            tile_data = [tile.rast.bands[0].data() for tile in tiles]

        if self.discrete:
            # Compute unique value counts for discrete rasters
            values, counts = numpy.unique(tile_data, return_counts=True)
        else:
            # Compute histogram for continuous rasters
            counts, bins = numpy.histogram(tile_data)
            # Compute bin labels
            values = []
            for i in range(len(bins) - 1):
                values.append((bins[i], bins[i + 1]))

        # If requested, convert counts into area
        if area:
            # Get scale of rasters in the geometry projection
            scalex, scaley = self.pixelsize(geom.srid, zoom)
            counts = counts * scalex * scaley

        return dict(zip(values, counts))
