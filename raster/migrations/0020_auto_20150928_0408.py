# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('raster', '0019_remove_rasterlayer_srid'),
    ]

    operations = [
        migrations.AddField(
            model_name='rasterlayermetadata',
            name='max_zoom',
            field=models.PositiveSmallIntegerField(null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='rasterlayermetadata',
            name='rasterlayer',
            field=models.OneToOneField(related_name='metadata', to='raster.RasterLayer'),
        ),
    ]
