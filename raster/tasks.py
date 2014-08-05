from celery import shared_task

@shared_task
def parse_raster_with_celery(rasterlayer):
    rasterlayer.parse()
