# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('raster', '0011_auto_20150615_0800'),
    ]

    operations = [
        migrations.AlterField(
            model_name='rasterlayer',
            name='nodata',
            field=models.CharField(max_length=100),
        ),
        migrations.AlterField(
            model_name='rasterlayer',
            name='srid',
            field=models.CharField(max_length=10),
        ),
    ]
