# -*- coding: utf-8 -*-
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('raster', '0018_rasterlayermetadata_srs_wkt'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='rasterlayer',
            name='srid',
        ),
    ]
