# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import django.contrib.postgres.fields
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('raster', '0023_remove_rasterlayer_parse_log'),
    ]

    operations = [
        migrations.CreateModel(
            name='RasterLayerBandMetadata',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('band', models.PositiveIntegerField()),
                ('nodata_value', models.FloatField(null=True)),
                ('max', models.FloatField()),
                ('min', models.FloatField()),
                ('hist_values', django.contrib.postgres.fields.ArrayField(base_field=models.FloatField(), size=100)),
                ('hist_bins', django.contrib.postgres.fields.ArrayField(base_field=models.FloatField(), size=101)),
            ],
        ),
        migrations.AlterField(
            model_name='rasterlayer',
            name='nodata',
            field=models.CharField(max_length=100, null=True, blank=True),
        ),
        migrations.AddField(
            model_name='rasterlayerbandmetadata',
            name='rasterlayer',
            field=models.ForeignKey(to='raster.RasterLayer'),
        ),
    ]
