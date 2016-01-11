# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('raster', '0028_auto_20160104_0533'),
    ]

    operations = [
        migrations.AddField(
            model_name='rasterlayerbandmetadata',
            name='mean',
            field=models.FloatField(null=True),
        ),
        migrations.AddField(
            model_name='rasterlayerbandmetadata',
            name='std',
            field=models.FloatField(null=True),
        ),
    ]
