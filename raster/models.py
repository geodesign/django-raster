from django.conf import settings
from django.db import models
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver

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

@receiver(pre_save, sender=RasterLayer)
def reset_parse_log_if_data_changed(sender, instance, **kwargs):
    try:
        obj = RasterLayer.objects.get(pk=instance.pk)
    except RasterLayer.DoesNotExist:
        pass
    else:
        if obj.rasterfile.name != instance.rasterfile.name:
            instance.parse_log = ''

@receiver(post_save, sender=RasterLayer)
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
    filename = models.TextField(null=True, blank=True)
