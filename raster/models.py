import json

from colorful.fields import RGBColorField

from django.conf import settings
from django.contrib.gis.db import models
from django.contrib.gis.gdal import Envelope, OGRGeometry, SpatialReference
from django.db.models import Max, Min
from django.db.models.signals import m2m_changed, post_save
from django.dispatch import receiver
from raster.const import WEB_MERCATOR_SRID
from raster.utils import hex_to_rgba
from raster.valuecount import ValueCountMixin


class LegendSemantics(models.Model):
    """
    Labels for pixel types (urban, forrest, warm, cold, etc)
    """
    name = models.CharField(max_length=50)
    description = models.TextField(null=True, blank=True)
    keyword = models.TextField(null=True, blank=True, max_length=100)

    def __str__(self):
        return self.name


class LegendEntry(models.Model):
    """
    One row in a Legend.
    """
    semantics = models.ForeignKey(LegendSemantics)
    expression = models.CharField(max_length=500,
            help_text='Use a number or a valid numpy logical expression '
                      'where x is the pixel value. For instance: "(-3.0 < x) '
                      '& (x <= 1)" or "x <= 1".')
    color = RGBColorField()

    def __str__(self):
        return '{}, {}, {}'.format(self.semantics.name,
                                   self.expression,
                                   self.color)


class Legend(models.Model):
    """
    Legend object for Rasters.
    """
    title = models.CharField(max_length=200)
    description = models.TextField(null=True, blank=True)
    entries = models.ManyToManyField(LegendEntry)
    json = models.TextField(null=True, blank=True)
    modified = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

    def update_json(self):
        data = []
        for val in self.entries.all():
            data.append({
                'name': val.semantics.name,
                'expression': val.expression,
                'color': val.color
            })
        self.json = json.dumps(data)

    @property
    def colormap(self):
        legend = json.loads(self.json)
        cmap = {}
        for leg in legend:
            cmap[leg['expression']] = hex_to_rgba(leg['color'])
        return cmap


def legend_entries_changed(sender, instance, action, **kwargs):
    """
    Updates style json upon adding or removing legend entries.
    """
    if action in ('post_add', 'post_remove'):
        instance.update_json()
        instance.save()

m2m_changed.connect(legend_entries_changed, sender=Legend.entries.through)


@receiver(post_save, sender=LegendEntry)
def update_dependent_legends_on_entry_change(sender, instance, **kwargs):
    """
    Updates dependent Legends on a change in Legend entries.
    """
    for legend in Legend.objects.filter(entries__id=instance.id):
        legend.update_json()
        legend.save()


@receiver(post_save, sender=LegendSemantics)
def update_dependent_legends_on_semantics_change(sender, instance, **kwargs):
    """
    Updates dependent Legends on a change in Semantics.
    """
    for entry in LegendEntry.objects.filter(semantics_id=instance.id):
        for legend in Legend.objects.filter(entries__id=entry.id):
            legend.update_json()
            legend.save()


class RasterLayer(models.Model, ValueCountMixin):
    """
    Source data model for raster layers
    """
    CONTINUOUS = 'co'
    CATEGORICAL = 'ca'
    MASK = 'ma'
    RANK_ORDERED = 'ro'

    DATATYPES = (
        (CONTINUOUS, 'Continuous'),
        (CATEGORICAL, 'Categorical'),
        (MASK, 'Mask'),
        (RANK_ORDERED, 'Rank Ordered')
    )

    name = models.CharField(max_length=100, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    datatype = models.CharField(max_length=2, choices=DATATYPES,
                                default='co')
    rasterfile = models.FileField(upload_to='rasters', null=True, blank=True)
    nodata = models.CharField(max_length=100)
    parse_log = models.TextField(blank=True, null=True, default='',
                                 editable=False)
    legend = models.ForeignKey(Legend, blank=True, null=True)
    modified = models.DateTimeField(auto_now=True)

    def __str__(self):
        return '{} {} (type: {})'.format(self.id, self.name, self.datatype)

    @property
    def discrete(self):
        """
        Returns true for discrete rasters.
        """
        return self.datatype in (self.CATEGORICAL, self.MASK, self.RANK_ORDERED)

    _bbox = None

    def extent(self, srid=WEB_MERCATOR_SRID):
        """
        Returns bbox for layer.
        """
        if not self._bbox:
            # Get bbox for raster in original coordinates
            meta = self.rasterlayermetadata
            xmin = meta.uperleftx
            ymax = meta.uperlefty
            xmax = xmin + meta.width * meta.scalex
            ymin = ymax + meta.height * meta.scaley

            # Create Polygon box
            geom = OGRGeometry(Envelope((xmin, ymin, xmax, ymax)).wkt)

            # Set original srs
            if meta.srs_wkt:
                geom.srs = SpatialReference(meta.srs_wkt)
            else:
                geom.srid = meta.srid

            # Transform to requested srid
            geom.transform(srid)

            # Calculate value range for bbox
            coords = geom.coords[0]
            xvals = [x[0] for x in coords]
            yvals = [x[1] for x in coords]

            # Set bbox
            self._bbox = (min(xvals), min(yvals), max(xvals), max(yvals))

        return self._bbox

    def index_range(self, zoom):
        """
        Returns the index range for
        """
        return self.rastertile_set.filter(tilez=zoom).aggregate(
            Min('tilex'), Max('tilex'), Min('tiley'), Max('tiley')
        )


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
        if hasattr(settings, 'RASTER_USE_CELERY') and settings.RASTER_USE_CELERY:
            from raster.tasks import parse_raster_layer_with_celery
            parse_raster_layer_with_celery.delay(instance)
        else:
            from raster.parser import RasterLayerParser
            parser = RasterLayerParser(instance)
            parser.parse_raster_layer()


class RasterLayerMetadata(models.Model):
    """
    Stores meta data for a raster layer
    """
    rasterlayer = models.OneToOneField(RasterLayer)
    uperleftx = models.FloatField(null=True, blank=True)
    uperlefty = models.FloatField(null=True, blank=True)
    width = models.IntegerField(null=True, blank=True)
    height = models.IntegerField(null=True, blank=True)
    scalex = models.FloatField(null=True, blank=True)
    scaley = models.FloatField(null=True, blank=True)
    skewx = models.FloatField(null=True, blank=True)
    skewy = models.FloatField(null=True, blank=True)
    numbands = models.IntegerField(null=True, blank=True)
    srs_wkt = models.TextField(null=True, blank=True)
    srid = models.PositiveSmallIntegerField(null=True, blank=True)

    def __str__(self):
        return self.rasterlayer.name


class RasterTile(models.Model):
    """
    Store individual tiles of a raster data source layer.
    """
    ZOOMLEVELS = (
        (1, 1), (2, 2), (3, 3), (4, 4), (5, 5), (6, 6), (7, 7),
        (8, 8), (9, 9), (10, 10), (11, 11), (12, 12), (13, 13),
        (14, 14), (15, 15), (16, 16), (17, 17), (18, 18)
    )
    rid = models.AutoField(primary_key=True)
    rast = models.RasterField(null=True, blank=True, srid=WEB_MERCATOR_SRID)
    rasterlayer = models.ForeignKey(RasterLayer, null=True, blank=True, db_index=True)
    filename = models.TextField(null=True, blank=True, db_index=True)
    tilex = models.IntegerField(db_index=True, null=True)
    tiley = models.IntegerField(db_index=True, null=True)
    tilez = models.IntegerField(db_index=True, null=True, choices=ZOOMLEVELS)

    def __str__(self):
        return '{0} {1}'.format(self.rid, self.filename)
