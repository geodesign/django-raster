from celery import task
from raster.parser import parse_raster_layer

@task
def parse_raster_layer_with_celery(rasterlayer):
   parse_raster_layer(rasterlayer)
