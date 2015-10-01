# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations


def move_srid_from_layer_to_metadata_forward(apps, schema_editor):
    """
    Copy srid from rasterlayers to metadata as a default value. This value will
    be overwritten automatically when parsing the layer.
    """
    RasterLayer = apps.get_model("raster", "RasterLayer")
    RasterLayerMetadata = apps.get_model("raster", "RasterLayerMetadata")
    for lyr in RasterLayer.objects.all():
        meta, created = RasterLayerMetadata.objects.get_or_create(rasterlayer=lyr)
        meta.srid = lyr.srid
        meta.save()


def move_srid_from_layer_to_metadata_backward(apps, schema_editor):
    """
    Copy the srids back to the raster layers.
    """
    RasterLayer = apps.get_model("raster", "RasterLayer")
    for lyr in RasterLayer.objects.all():
        if hasattr(lyr, 'rasterlayermetadata'):
            lyr.srid = lyr.rasterlayermetadata.srid
            lyr.save()


class Migration(migrations.Migration):

    dependencies = [
        ('raster', '0016_rasterlayermetadata_srid'),
    ]

    operations = [
        migrations.RunPython(move_srid_from_layer_to_metadata_forward, move_srid_from_layer_to_metadata_backward),
    ]
