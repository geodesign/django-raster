from celery import task
from raster.parser import RasterLayerParser

@task
def parse_raster_layer_with_celery(rasterlayer):
    """Wrapper to all the raster parser as a celery task"""
    parser = RasterLayerParser(rasterlayer)
    parser.parse_raster_layer()
