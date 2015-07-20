# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('raster', '0012_auto_20150616_0538'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='rasterlayer',
            name='max_zoom',
        ),
    ]
