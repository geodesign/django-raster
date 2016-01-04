# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import django.contrib.postgres.fields
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('raster', '0027_rasterlayerreprojected'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='rasterlayerparsestatus',
            name='tile_level',
        ),
        migrations.AddField(
            model_name='rasterlayerparsestatus',
            name='tile_levels',
            field=django.contrib.postgres.fields.ArrayField(default=[], base_field=models.PositiveIntegerField(), size=None),
        ),
    ]
