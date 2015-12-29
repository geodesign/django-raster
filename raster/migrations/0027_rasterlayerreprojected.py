# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('raster', '0026_auto_20151120_1334'),
    ]

    operations = [
        migrations.CreateModel(
            name='RasterLayerReprojected',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('rasterfile', models.FileField(null=True, upload_to=b'rasters/reprojected', blank=True)),
                ('rasterlayer', models.OneToOneField(related_name='reprojected', to='raster.RasterLayer')),
            ],
        ),
    ]
