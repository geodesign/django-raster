# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib.gis.db import models
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='RasterLayer',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=100, null=True, blank=True)),
                ('description', models.TextField(null=True, blank=True)),
                ('datatype', models.CharField(default=b'co', max_length=2, choices=[(b'co', b'Continuous'), (b'ca', b'Categorical'), (b'ma', b'Mask'), (b'ro', b'Rank Ordered')])),
                ('rasterfile', models.FileField(upload_to=b'rasters')),
                ('srid', models.CharField(default=b'3086', max_length=10)),
                ('nodata', models.CharField(default=b'-9999', max_length=100)),
                ('parse_log', models.TextField(default=b'', null=True, editable=False, blank=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='RasterTile',
            fields=[
                ('rid', models.AutoField(serialize=False, primary_key=True)),
                ('rast', models.RasterField(null=True, blank=True)),
                ('filename', models.TextField(null=True, blank=True)),
                ('rasterlayer', models.ForeignKey(blank=True, to='raster.RasterLayer', null=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
    ]
