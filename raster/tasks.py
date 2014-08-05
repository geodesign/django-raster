from celery import task
from raster.parser import parse_raster_layer

@task
def parse_raster_layer_with_celery(rasterlayer):
    """Wrapper to all the raster parser as a celery task"""
    parse_raster_layer(rasterlayer)
