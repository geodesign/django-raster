from django.conf import settings
from django.db import models, connection
from django.dispatch import receiver
from django.contrib.gis.geos import GEOSGeometry

from raster.fields import RasterField

class RasterLayer(models.Model):
    """Source data model for raster layers"""

    DATATYPES = (('co', 'Continuous'),
                 ('ca', 'Categorical'),
                 ('ma', 'Mask'),
                 ('ro', 'Rank Ordered'))

    name = models.CharField(max_length=100, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    datatype = models.CharField(max_length=2, choices=DATATYPES,
                                default='co')
    rasterfile = models.FileField(upload_to='rasters')
    srid = models.CharField(max_length=10, default='3086')
    nodata = models.CharField(max_length=100, default='-9999')
    parse_log = models.TextField(blank=True, null=True, default='',
                                 editable=False)

    def __unicode__(self):
        count = self.rastertile_set.count()
        if count:
            info = str(count) + ' raster tiles'
        else:
            info = 'not parsed yet'
        return '{name} ({info})'.format(name=self.name, info=info)

    def _collect_tiles_sql(self, level=0):
        """SQL query string for selecting all tiles for this layer"""
        return "SELECT rast, level FROM raster_rastertile \
                WHERE rasterlayer_id={0} AND level={1}".format(self.id, level)
    
    def _clip_tiles_sql(self, geom, level=0):
        """Returns intersection of tiles with geom"""
        return "SELECT ST_Clip(rast, ST_GeomFromText('{geom}')) AS rast \
                FROM ({base}) AS cliptiles \
                WHERE ST_Intersects(rast, ST_GeomFromText('{geom}'))\
                ".format(geom=geom.ewkt, base=self._collect_tiles_sql(level))

    def _value_count_sql(self, geom):
        """SQL query string for counting pixels per distinct value"""
        if geom:
            tile_sql = self._clip_tiles_sql(geom)
        else:
            tile_sql = self._collect_tiles_sql()

        count_sql = "SELECT ST_ValueCount(rast) AS pvc\
                     FROM ({0}) AS cliprast WHERE ST_Count(rast) != 0\
                     ".format(tile_sql)

        return "SELECT (pvc).value, SUM((pvc).count) AS count FROM \
                ({0}) AS pvctable GROUP BY (pvc).value".format(count_sql)

    def value_count(self, geom=None):
        """Get a count by distinct pixel value within the given geometry"""
        # Check that raster is categorical or mask
        if not self.datatype in ['ca', 'ma']:
            raise TypeError('Wrong rastertype, value counts can only be '\
                            'calculated for categorical or mask raster tpyes')

        # Make sure geometry is GEOS Geom
        if geom:
            geom = GEOSGeometry(geom)
            geom.transform(self.srid)
        # Query data and return results
        cursor = connection.cursor()
        cursor.execute(self._value_count_sql(geom))
        # Retruns all rows as dict
        desc = cursor.description
        return [
            dict(zip([col[0] for col in desc], row))
            for row in cursor.fetchall()
        ]

    _pixelsize = None

    def _pixelsize_sql(self, level=1):
        """SQL query string to get pixel size in the units of the layer"""
        return "SELECT ST_ScaleX(rast) AS scalex, ST_ScaleY(rast) AS scaley\
                FROM ({0}) AS tiles LIMIT 1"\
                .format(self._collect_tiles_sql(level))

    def pixelsize(self, level=1):
        """Returns pixel area in units of raster layer"""
        if not self._pixelsize:
            cursor = connection.cursor()
            cursor.execute(self._pixelsize_sql(level))
            res = cursor.fetchone()
            self._pixelsize = (abs(res[0]), abs(res[1]))

        return self._pixelsize

@receiver(models.signals.pre_save, sender=RasterLayer)
def reset_parse_log_if_data_changed(sender, instance, **kwargs):
    try:
        obj = RasterLayer.objects.get(pk=instance.pk)
    except RasterLayer.DoesNotExist:
        pass
    else:
        if obj.rasterfile.name != instance.rasterfile.name:
            instance.parse_log = ''

@receiver(models.signals.post_save, sender=RasterLayer)
def parse_raster_layer_if_log_is_empty(sender, instance, **kwargs):
    if instance.rasterfile.name and instance.parse_log == '':
        if hasattr(settings, 'RASTER_USE_CELERY') and\
                                settings.RASTER_USE_CELERY:
            from raster.tasks import parse_raster_layer_with_celery
            parse_raster_layer_with_celery.delay(instance)
        else:
            from raster.parser import RasterLayerParser
            parser = RasterLayerParser(instance)
            parser.parse_raster_layer()

class RasterTile(models.Model):
    """Model to store individual tiles of a raster data source layer"""
    rid = models.AutoField(primary_key=True)
    rast = RasterField(null=True, blank=True)
    rasterlayer = models.ForeignKey(RasterLayer, null=True, blank=True)
    filename = models.TextField(null=True, blank=True, db_index=True)
    level = models.IntegerField(db_index=True)
    def __unicode__(self):
        return '{0} {1}'.format(self.rid, self.filename)
