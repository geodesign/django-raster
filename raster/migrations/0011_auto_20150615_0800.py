# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import django.contrib.gis.db.models.fields
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('raster', '0010_auto_20150429_1207'),
    ]

    operations = [
        migrations.AlterField(
            model_name='rastertile',
            name='rast',
            field=django.contrib.gis.db.models.fields.RasterField(srid=3857, null=True, blank=True),
        ),
    ]
