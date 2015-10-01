# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('raster', '0015_auto_20150819_0320'),
    ]

    operations = [
        migrations.AddField(
            model_name='rasterlayermetadata',
            name='srid',
            field=models.PositiveSmallIntegerField(null=True, blank=True),
        ),
    ]
