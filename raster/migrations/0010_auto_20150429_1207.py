# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('raster', '0009_rasterlayer_max_zoom'),
    ]

    operations = [
        migrations.AlterField(
            model_name='legendentry',
            name='expression',
            field=models.CharField(help_text=b'Use a number or a valid numpy logical expression where x is the pixel value. For instance: "(-3.0 < x) & (x <= 1)" or "x <= 1".', max_length=500),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='rasterlayer',
            name='rasterfile',
            field=models.FileField(null=True, upload_to=b'rasters', blank=True),
            preserve_default=True,
        ),
    ]
