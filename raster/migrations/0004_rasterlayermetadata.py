# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('raster', '0003_rastertile_level'),
    ]

    operations = [
        migrations.CreateModel(
            name='RasterLayerMetadata',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('uperleftx', models.FloatField(null=True, blank=True)),
                ('uperlefty', models.FloatField(null=True, blank=True)),
                ('width', models.IntegerField(null=True, blank=True)),
                ('height', models.IntegerField(null=True, blank=True)),
                ('scalex', models.FloatField(null=True, blank=True)),
                ('scaley', models.FloatField(null=True, blank=True)),
                ('skewx', models.FloatField(null=True, blank=True)),
                ('skewy', models.FloatField(null=True, blank=True)),
                ('numbands', models.IntegerField(null=True, blank=True)),
                ('rasterlayer', models.OneToOneField(to='raster.RasterLayer')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
    ]
