# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('raster', '0004_rasterlayermetadata'),
    ]

    operations = [
        migrations.RunSQL(
            "DROP INDEX IF EXISTS raster_rastertile_rast_st_convexhull_idx; CREATE INDEX raster_rastertile_rast_st_convexhull_idx\
             ON raster_rastertile USING gist( ST_ConvexHull(rast) )",
            "DROP INDEX IF EXISTS raster_rastertile_rast_st_convexhull_idx"
        )
    ]
