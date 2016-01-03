from celery import group, task

from django.dispatch import Signal
from raster.tiles.const import GLOBAL_MAX_ZOOM_LEVEL
from raster.tiles.parser import RasterLayerParser

rasterlayers_parser_ended = Signal(providing_args=['instance'])


@task
def create_tiles(rasterlayer, zoom):
    """
    Create all tiles for a raster layer at the input zoom level.
    """
    parser = RasterLayerParser(rasterlayer)
    parser.get_raster_file()
    parser.compute_max_zoom()
    parser.create_tiles(zoom)


@task
def drop_all_tiles(rasterlayer):
    """
    Drop all tiles of a rasterlayer.
    """
    parser = RasterLayerParser(rasterlayer)
    parser.drop_all_tiles()


@task
def drop_empty_tiles(rasterlayer):
    """
    Drop empty tiles of a raster layer.
    """
    parser = RasterLayerParser(rasterlayer)
    parser.drop_empty_rasters()


@task
def send_success_signal(rasterlayer):
    """
    Send parse end succes signal and log success to rasterlayer.
    """
    rasterlayers_parser_ended.send(sender=rasterlayer.__class__, instance=rasterlayer)

    # Log success of parsing
    parser = RasterLayerParser(rasterlayer)
    parser.log(
        'Successfully finished parsing raster',
        status=rasterlayer.parsestatus.FINISHED
    )


@task
def parse_raster_layer(rasterlayer):
    """
    Parse input raster layer through a asynchronous task chain.
    """
    parser = RasterLayerParser(rasterlayer)

    parser.log(
        'Started parsing raster file',
        reset=True,
        status=rasterlayer.parsestatus.DOWNLOADING_FILE
    )

    parsing_task_chain = (
        drop_all_tiles.si(rasterlayer) |
        group(create_tiles.si(rasterlayer, zoom) for zoom in range(GLOBAL_MAX_ZOOM_LEVEL + 1)) |
        drop_empty_tiles.si(rasterlayer) |
        send_success_signal.si(rasterlayer)
    )

    parsing_task_chain.apply_async()
