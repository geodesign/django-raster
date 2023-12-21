# -*- coding: utf-8 -*-
from django.db import migrations

def forward(apps, schema_editor):
    migrations.RunSQL(
            "DROP INDEX IF EXISTS raster_rastertile_rast_st_convexhull_idx;\
            CREATE INDEX raster_rastertile_rast_st_convexhull_idx ON raster_rastertile USING gist( ST_ConvexHull(rast) )"
    )
def reverse(apps, schema_editor):
    migrations.RunSQL(
            "DROP INDEX IF EXISTS raster_rastertile_rast_st_convexhull_idx"
    )

class Migration(migrations.Migration):

    dependencies = [
        ('raster', '0004_rasterlayermetadata'),
    ]
    
    operations = [
        migrations.RunPython(forward, reverse),
    ]