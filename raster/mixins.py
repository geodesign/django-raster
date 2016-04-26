from __future__ import unicode_literals

from django.contrib.gis.geos import GEOSGeometry
from django.db import connection
from raster.tiles.const import WEB_MERCATOR_SRID


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
        from raster.valuecount import Aggregator
        agg = Aggregator(layer_dict={'a': self.id}, formula='a', zoom=zoom, geom=geom, acres=area)
        return agg.value_count()
