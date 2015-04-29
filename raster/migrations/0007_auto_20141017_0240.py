# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('raster', '0006_auto_20141016_0522'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='rastertile',
            name='level',
        ),
        migrations.AddField(
            model_name='rastertile',
            name='is_base',
            field=models.BooleanField(default=False),
            preserve_default=True,
        ),
    ]
