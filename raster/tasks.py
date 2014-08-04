from celery import task

@task
def parse_raster_with_celery(rasterlayer):
    rasterlayer.parse()
