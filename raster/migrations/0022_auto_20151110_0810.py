# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations


def move_parse_log_to_parse_status_objects_forward(apps, schema_editor):
    """
    Copy parse status data to new objects.
    """
    RasterLayer = apps.get_model("raster", "RasterLayer")
    RasterLayerParseStatus = apps.get_model("raster", "RasterLayerParseStatus")
    for lyr in RasterLayer.objects.all():
        status, created = RasterLayerParseStatus.objects.get_or_create(rasterlayer=lyr)
        status.log = lyr.parse_log
        if 'Successfully finished parsing raster' in lyr.parse_log:
            status.status = 5  # Finished
        else:
            status.status = 6  # Failed
        status.save()


def move_parse_log_to_parse_status_objects_backward(apps, schema_editor):
    """
    Copy the srids back to the raster layers.
    """
    RasterLayer = apps.get_model("raster", "RasterLayer")
    for lyr in RasterLayer.objects.all():
        if hasattr(lyr, 'parsestatus'):
            lyr.parse_log = lyr.parsestatus.log
            lyr.save()


class Migration(migrations.Migration):

    dependencies = [
        ('raster', '0021_rasterlayerparsestatus'),
    ]

    operations = [
        migrations.RunPython(
            move_parse_log_to_parse_status_objects_forward,
            move_parse_log_to_parse_status_objects_backward
        )
    ]
