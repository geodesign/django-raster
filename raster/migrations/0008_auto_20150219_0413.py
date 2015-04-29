# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import colorful.fields

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('raster', '0007_auto_20141017_0240'),
    ]

    operations = [
        migrations.CreateModel(
            name='Legend',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('title', models.CharField(max_length=200)),
                ('description', models.TextField(null=True, blank=True)),
                ('json', models.TextField(null=True, blank=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='LegendEntry',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('expression', models.CharField(max_length=500)),
                ('color', colorful.fields.RGBColorField()),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='LegendSemantics',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=50)),
                ('description', models.TextField(null=True, blank=True)),
                ('keyword', models.TextField(max_length=100, null=True, blank=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AddField(
            model_name='legendentry',
            name='semantics',
            field=models.ForeignKey(to='raster.LegendSemantics'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='legend',
            name='entries',
            field=models.ManyToManyField(to='raster.LegendEntry'),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='rasterlayer',
            name='legend',
            field=models.ForeignKey(blank=True, to='raster.Legend', null=True),
            preserve_default=True,
        ),
    ]
