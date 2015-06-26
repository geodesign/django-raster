from django.contrib.gis.geos import GEOSGeometry
from django.db import connection
from raster.const import WEB_MERCATOR_SRID


class ValueCountMixin(object):
    """
    Value count methods for Raster Layers.
    """
    def _collect_tiles_sql(self, srid=None):
        """
        SQL query string for selecting all tiles at the maximum zoom level
        for this layer.
        """
        if srid:
            sql_head = "SELECT ST_Transform(rast, {srid}) AS rast FROM raster_rastertile "
        else:
            sql_head = "SELECT rast FROM raster_rastertile "

        return (
            sql_head +
            "WHERE rasterlayer_id={layer_id} "
            "AND tilez=(SELECT MAX(tilez) FROM raster_rastertile WHERE rasterlayer_id={layer_id})"
        ).format(srid=srid, layer_id=self.id)

    def _clip_tiles_sql(self, geom):
        """
        Returns intersection of tiles with geom.
        """
        # Make intersection on raw tiles to leverage index, clip in the geom's srid
        var = (
            "SELECT ST_Clip(ST_Transform(rast, {srid}), ST_GeomFromText('{geom}')) AS rast "
            "FROM ({base}) AS cliptiles "
            "WHERE ST_Intersects(rast, ST_Transform(ST_GeomFromText('{geom}'), {wmerc}))"
        ).format(
            srid=geom.srid,
            geom=geom.ewkt,
            base=self._collect_tiles_sql(),
            wmerc=WEB_MERCATOR_SRID
        )
        return var

    def _value_count_sql(self, geom):
        """
        SQL query string for counting pixels per distinct value.
        """
        if geom:
            tile_sql = self._clip_tiles_sql(geom)
        else:
            tile_sql = self._collect_tiles_sql()

        count_sql = (
            "SELECT ST_ValueCount(rast) AS pvc "
            "FROM ({0}) AS cliprast WHERE ST_Count(rast) != 0"
        ).format(tile_sql)

        return (
            "SELECT (pvc).value, SUM((pvc).count) AS count FROM "
            "({0}) AS pvctable GROUP BY (pvc).value"
        ).format(count_sql)

    def value_count(self, geom=None, area=False):
        """
        Get a count by distinct pixel value within the given geometry.
        """
        # Check that raster is categorical or mask
        if self.datatype not in ['ca', 'ma']:
            raise TypeError('Wrong rastertype, value counts can only be '
                            'calculated for categorical or mask raster tpyes')

        if geom:
            # Make sure geometry is GEOS Geom
            geom = GEOSGeometry(geom)

        # Query data and return results
        cursor = connection.cursor()
        cursor.execute(self._value_count_sql(geom))

        # Convert value count to areas if requested
        if area:
            scalex, scaley = self._min_pixelsize(geom.srid)
            return {int(row[0]): int(row[1]) * scalex * scaley for row in cursor.fetchall()}
        else:
            return {int(row[0]): int(row[1]) for row in cursor.fetchall()}

    def _min_pixelsize(self, srid=WEB_MERCATOR_SRID):
        sql = (
            "SELECT ST_ScaleX(rast) AS scalex, ST_ScaleY(rast) AS scaley "
            "FROM ({0}) AS cliprast "
            "LIMIT 1"
        ).format(self._collect_tiles_sql(srid))

        cursor = connection.cursor()
        cursor.execute(sql)
        res = cursor.fetchone()
        return (abs(res[0]), abs(res[1]))
