# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('raster', '0002_auto_20140925_0723'),
    ]

    operations = [
        migrations.AddField(
            model_name='rastertile',
            name='level',
            field=models.IntegerField(default=1, db_index=True),
            preserve_default=False,
        ),
    ]
