# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('raster', '0024_auto_20151111_0532'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='rastertile',
            name='filename',
        ),
        migrations.AlterField(
            model_name='legendentry',
            name='expression',
            field=models.CharField(help_text=b'Use a number or a valid numpy logical expression where x is thepixel value. For instance: "(-3.0 < x) & (x <= 1)" or "x <= 1".', max_length=500),
        ),
        migrations.AlterField(
            model_name='rasterlayer',
            name='nodata',
            field=models.CharField(help_text=b'Leave blank to keep the internal band nodata values. If a nodatavalue is specified here, it will be used for all bands of this raster.', max_length=100, null=True, blank=True),
        ),
    ]
