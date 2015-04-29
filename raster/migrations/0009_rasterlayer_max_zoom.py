# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('raster', '0008_auto_20150219_0413'),
    ]

    operations = [
        migrations.AddField(
            model_name='rasterlayer',
            name='max_zoom',
            field=models.IntegerField(null=True, blank=True),
            preserve_default=True,
        ),
    ]
