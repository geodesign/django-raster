import shutil
import traceback

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
    try:
        parser = RasterLayerParser(rasterlayer)
        parser.open_raster_file()
        parser.compute_max_zoom()
        parser.create_tiles(zoom)
    except:
        parser.log(
            traceback.format_exc(),
            status=parser.rasterlayer.parsestatus.FAILED
        )
        raise
    finally:
        if hasattr(parser, 'tmpdir'):
            shutil.rmtree(parser.tmpdir)


@task
def clear_tiles(rasterlayer):
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
    parser.drop_empty_tiles()


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
def open_and_reproject_raster(rasterlayer, reset=False):
    """
    Initializes parser, creates reprojected raster copy if necessary.
    """
    try:
        parser = RasterLayerParser(rasterlayer)
        if reset:
            parser.log(
                'Started parsing raster file',
                reset=True,
                status=rasterlayer.parsestatus.DOWNLOADING_FILE
            )
        parser.open_raster_file()
    except:
        parser.log(
            traceback.format_exc(),
            status=parser.rasterlayer.parsestatus.FAILED
        )
        raise
    finally:
        if hasattr(parser, 'tmpdir'):
            shutil.rmtree(parser.tmpdir)


def parse_raster_layer(rasterlayer, async=True):
    """
    Parse input raster layer through a asynchronous task chain.
    """
    if async:
        # Grouped parsing: the first is a single task for the first five zoom
        # levels, as download time might be bigger than parsing time for lower
        # zoom levels. The middle is a group of the next five zoom levels,
        # being parsed in parallel but, the rest is parsed in parallel at the
        # after the middle is finished.
        first = create_tiles.si(rasterlayer, range(GLOBAL_MAX_ZOOM_LEVEL + 1)[:5])
        middle = group(create_tiles.si(rasterlayer, zoom) for zoom in range(GLOBAL_MAX_ZOOM_LEVEL + 1)[5:10])
        last = group(create_tiles.si(rasterlayer, zoom) for zoom in range(GLOBAL_MAX_ZOOM_LEVEL + 1)[10:])

        parsing_task_chain = (
            open_and_reproject_raster.si(rasterlayer) |
            clear_tiles.si(rasterlayer) |
            first |
            middle |
            last |
            drop_empty_tiles.si(rasterlayer) |
            send_success_signal.si(rasterlayer)
        )
        parsing_task_chain.apply_async()
    else:
        open_and_reproject_raster(rasterlayer)
        clear_tiles(rasterlayer)
        for zoom in range(GLOBAL_MAX_ZOOM_LEVEL + 1):
            create_tiles(rasterlayer, zoom)
        drop_empty_tiles(rasterlayer)
        send_success_signal(rasterlayer)
