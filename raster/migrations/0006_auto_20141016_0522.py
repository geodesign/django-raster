# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('raster', '0005_auto_20141014_0955'),
    ]

    operations = [
        migrations.AddField(
            model_name='rastertile',
            name='tilex',
            field=models.IntegerField(null=True, db_index=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='rastertile',
            name='tiley',
            field=models.IntegerField(null=True, db_index=True),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='rastertile',
            name='tilez',
            field=models.IntegerField(db_index=True, null=True, choices=[(1, 1), (2, 2), (3, 3), (4, 4), (5, 5), (6, 6), (7, 7), (8, 8), (9, 9), (10, 10), (11, 11), (12, 12), (13, 13), (14, 14), (15, 15), (16, 16), (17, 17), (18, 18)]),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='rastertile',
            name='level',
            field=models.IntegerField(null=True, db_index=True),
        ),
    ]
