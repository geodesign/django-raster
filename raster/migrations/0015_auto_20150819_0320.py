# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import datetime

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('raster', '0014_remove_rastertile_is_base'),
    ]

    operations = [
        migrations.AddField(
            model_name='legend',
            name='modified',
            field=models.DateTimeField(default=datetime.datetime(2015, 8, 19, 3, 20, 29, 439201), auto_now=True),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='rasterlayer',
            name='modified',
            field=models.DateTimeField(default=datetime.datetime(2015, 8, 19, 3, 20, 37, 663400), auto_now=True),
            preserve_default=False,
        ),
    ]
