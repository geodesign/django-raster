# -*- coding: utf-8 -*-
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('raster', '0025_auto_20151113_0259'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='rasterlayerbandmetadata',
            unique_together=set([('rasterlayer', 'band')]),
        ),
    ]
