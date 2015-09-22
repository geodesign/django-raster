# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('raster', '0017_copy_srids_20150922_0207'),
    ]

    operations = [
        migrations.AddField(
            model_name='rasterlayermetadata',
            name='srs_wkt',
            field=models.TextField(null=True, blank=True),
        ),
    ]
