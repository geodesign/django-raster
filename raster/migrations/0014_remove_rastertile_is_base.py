# -*- coding: utf-8 -*-
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('raster', '0013_remove_rasterlayer_max_zoom'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='rastertile',
            name='is_base',
        ),
    ]
