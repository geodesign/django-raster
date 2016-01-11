# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import django.contrib.postgres.fields
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('raster', '0029_auto_20160111_0646'),
    ]

    operations = [
        migrations.AlterField(
            model_name='rasterlayerbandmetadata',
            name='hist_values',
            field=django.contrib.postgres.fields.ArrayField(base_field=models.BigIntegerField(), size=100),
        ),
    ]
