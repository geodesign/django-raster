# Generated by Django 2.1.7 on 2019-03-13 07:28

import django.contrib.postgres.fields
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('raster', '0038_auto_20171116_1027'),
    ]

    operations = [
        migrations.AlterField(
            model_name='rasterlayerparsestatus',
            name='tile_levels',
            field=django.contrib.postgres.fields.ArrayField(base_field=models.PositiveIntegerField(), default=list, size=None),
        ),
    ]