import json
import math

import numpy
from celery import group
from colorful.fields import RGBColorField

from django.conf import settings
from django.contrib.gis.db import models
from django.contrib.gis.gdal import Envelope, OGRGeometry, SpatialReference
from django.contrib.postgres.fields import ArrayField
from django.db.models import Max, Min
from django.db.models.signals import m2m_changed, post_save, pre_save
from django.dispatch import receiver
from raster.mixins import ValueCountMixin
from raster.tiles.const import GLOBAL_MAX_ZOOM_LEVEL, WEB_MERCATOR_SRID
from raster.utils import hex_to_rgba


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
        help_text='Use a number or a valid numpy logical expression where x is the'
                  'pixel value. For instance: "(-3.0 < x) & (x <= 1)" or "x <= 1".')
    color = RGBColorField()

    def __str__(self):
        return '{}, {}, {}'.format(self.semantics.name, self.expression, self.color)


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

    def save(self, *args, **kwargs):
        if self.id:
            self.update_json()
        super(Legend, self).save(*args, **kwargs)


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
    datatype = models.CharField(max_length=2, choices=DATATYPES, default='co')
    rasterfile = models.FileField(upload_to='rasters', null=True, blank=True)
    nodata = models.CharField(max_length=100, null=True, blank=True,
        help_text='Leave blank to keep the internal band nodata values. If a nodata '
                  'value is specified here, it will be used for all bands of this raster.')
    srid = models.IntegerField(null=True, blank=True,
        help_text='Leave blank to use the internal raster srid. If a srid is '
                  'specified here, it will be used for all calculations.')
    max_zoom = models.IntegerField(null=True, blank=True,
        help_text='Leave blank to automatically determine the max zoom level '
                  'from the raster scale. Otherwise the raster parsed up to '
                  'the zoom level specified here.')
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
    _bbox_srid = None

    def extent(self, srid=WEB_MERCATOR_SRID):
        """
        Returns bbox for layer.
        """
        if not self._bbox or self._bbox_srid != srid:
            # Get bbox for raster in original coordinates
            meta = self.metadata
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
            self._bbox_srid = srid
        return self._bbox

    def index_range(self, zoom):
        """
        Compute the index range for this rasterlayer at a given zoom leve.
        """
        return self.rastertile_set.filter(tilez=zoom).aggregate(
            Min('tilex'), Max('tilex'), Min('tiley'), Max('tiley')
        )

    def parse(self):
        """
        Parse raster layer to extract metadata and create tiles.
        """
        from raster.tasks import open_and_reproject_raster, create_tiles, clear_tiles, send_success_signal
        from raster.tiles.parser import RasterLayerParser

        # Check if parsing should happen asynchronously
        async = getattr(settings, 'RASTER_USE_CELERY', False)

        # Create array of all allowed zoom levels
        zoom_range = range(GLOBAL_MAX_ZOOM_LEVEL + 1)

        if async:
            # Bundle the first five raster layers to one task, downloading is
            # more costly than the parsing itself.
            high_level_bundle = create_tiles.si(self, zoom_range[:5])

            # Create a group of tasks with the middle level zoom levels that should
            # be prioritized.
            middle_level_group = group(
                create_tiles.si(self, zoom) for zoom in zoom_range[5:10]
            )
            # Combine bundle and middle levels to priority group
            priority_group = group(high_level_bundle, middle_level_group)

            # Create a task group for high zoom levels
            high_level_group = group(create_tiles.si(self, zoom) for zoom in zoom_range[10:])

            # Setup the parser logic as parsing chain
            parsing_task_chain = (
                open_and_reproject_raster.si(self) |
                clear_tiles.si(self) |
                priority_group |
                high_level_group |
                send_success_signal.si(self)
            )

            # Apply the parsing chain
            parsing_task_chain.apply_async()

            parser = RasterLayerParser(self)
            parser.log('Parse task queued, waiting for worker availability.')
        else:
            open_and_reproject_raster(self)
            clear_tiles(self)
            for zoom in zoom_range:
                create_tiles(self, zoom)
            send_success_signal(self)


@receiver(pre_save, sender=RasterLayer)
def reset_parse_log_if_data_changed(sender, instance, **kwargs):
    try:
        obj = RasterLayer.objects.get(pk=instance.pk)
    except RasterLayer.DoesNotExist:
        pass
    else:
        # If filename or nodata value has changed, clear parse status to
        # trigger re-parsing. Also remove the reprojected copy of the previous
        # file if it exists.
        if (obj.rasterfile.name != instance.rasterfile.name or
                obj.nodata != instance.nodata or
                obj.max_zoom != instance.max_zoom or
                obj.srid != instance.srid):
            instance.parsestatus.reset()
            if hasattr(instance, 'reprojected'):
                reproj = instance.reprojected
                reproj.delete()


@receiver(post_save, sender=RasterLayer)
def parse_raster_layer_if_status_is_unparsed(sender, instance, created, **kwargs):
    RasterLayerMetadata.objects.get_or_create(rasterlayer=instance)
    status, created = RasterLayerParseStatus.objects.get_or_create(rasterlayer=instance)

    if instance.rasterfile.name and status.status == status.UNPARSED:
        instance.parse()


class RasterLayerReprojected(models.Model):
    """
    Stores reprojected version of raster.
    """
    rasterlayer = models.OneToOneField(RasterLayer, related_name='reprojected')
    rasterfile = models.FileField(upload_to='rasters/reprojected', null=True, blank=True)

    def __str__(self):
        return self.rasterlayer.name


class RasterLayerMetadata(models.Model):
    """
    Stores meta data for a raster layer
    """
    rasterlayer = models.OneToOneField(RasterLayer, related_name='metadata')
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
    max_zoom = models.PositiveSmallIntegerField(null=True, blank=True)

    def __str__(self):
        return self.rasterlayer.name


class RasterLayerParseStatus(models.Model):
    """
    Tracks the parsing status of the raster layer.
    """
    UNPARSED = 0
    DOWNLOADING_FILE = 1
    REPROJECTING_RASTER = 2
    CREATING_TILES = 3
    DROPPING_EMPTY_TILES = 4
    FINISHED = 5
    FAILED = 6

    STATUS_CHOICES = (
        (UNPARSED, 'Layer not yet parsed'),
        (DOWNLOADING_FILE, 'Downloading file'),
        (REPROJECTING_RASTER, 'Reprojecting'),
        (CREATING_TILES, 'Creating tiles'),
        (DROPPING_EMPTY_TILES, 'Dropping empty tiles'),
        (FINISHED, 'Finished parsing'),
        (FAILED, 'Failed parsing'),
    )
    rasterlayer = models.OneToOneField(RasterLayer, related_name='parsestatus')
    status = models.IntegerField(choices=STATUS_CHOICES, default=UNPARSED)
    log = models.TextField(default='', editable=False)
    tile_levels = ArrayField(models.PositiveIntegerField(), default=[])

    def __str__(self):
        return '{0} - {1}'.format(self.rasterlayer.name, self.get_status_display())

    def reset(self):
        self.tile_levels = []
        self.log = ''
        self.status = self.UNPARSED
        self.save()


class RasterLayerBandMetadata(models.Model):

    HISTOGRAM_BINS = 100

    rasterlayer = models.ForeignKey(RasterLayer)
    band = models.PositiveIntegerField()
    nodata_value = models.FloatField(null=True)
    min = models.FloatField()
    max = models.FloatField()
    mean = models.FloatField(null=True)
    std = models.FloatField(null=True)
    hist_values = ArrayField(models.BigIntegerField(), size=HISTOGRAM_BINS)
    hist_bins = ArrayField(models.FloatField(), size=HISTOGRAM_BINS + 1)

    class Meta:
        unique_together = ('rasterlayer', 'band')

    def __str__(self):
        return '{} - Min {} - Max {}'.format(self.rasterlayer.name, self.min, self.max)

    def save(self, *args, **kwargs):
        if not self.pk:
            # Construct empty histogram
            hist = numpy.histogram(
                [],
                range=(math.floor(self.min), math.ceil(self.max)),
                bins=self.HISTOGRAM_BINS
            )
            # Set empty histogram values
            self.hist_values = hist[0].tolist()
            self.hist_bins = hist[1].tolist()

        super(RasterLayerBandMetadata, self).save(*args, **kwargs)

    def statistics(self):
        return (self.min, self.max, self.mean, self.std)


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
    tilex = models.IntegerField(db_index=True, null=True)
    tiley = models.IntegerField(db_index=True, null=True)
    tilez = models.IntegerField(db_index=True, null=True, choices=ZOOMLEVELS)

    def __str__(self):
        return '{} {}'.format(self.rid, self.rasterlayer.name)
