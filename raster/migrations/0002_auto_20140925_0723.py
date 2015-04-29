# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('raster', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='rastertile',
            name='filename',
            field=models.TextField(db_index=True, null=True, blank=True),
        ),
    ]
