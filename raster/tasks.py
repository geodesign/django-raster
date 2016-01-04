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
    # Log success of parsing
    parser = RasterLayerParser(rasterlayer)
    parser.log(
        'Successfully finished parsing raster',
        status=rasterlayer.parsestatus.FINISHED
    )
    rasterlayers_parser_ended.send(sender=rasterlayer.__class__, instance=rasterlayer)


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
    zoom_range = range(GLOBAL_MAX_ZOOM_LEVEL + 1)

    if async:
        # Bundle the first five raster layers to one task, downloading is
        # more costly than the parsing itself.
        high_level_bundle = create_tiles.si(rasterlayer, zoom_range[:5])

        # Create a group of tasks with the middle level zoom levels that should
        # be prioritized.
        middle_level_group = group(
            create_tiles.si(rasterlayer, zoom) for zoom in zoom_range[5:10]
        )
        # Combine bundle and middle levels to priority group
        priority_group = group(high_level_bundle, middle_level_group)

        # Create a task group for high zoom levels
        high_level_group = group(create_tiles.si(rasterlayer, zoom) for zoom in zoom_range[10:])

        # Setup the parser logic as parsing chain
        parsing_task_chain = (
            open_and_reproject_raster.si(rasterlayer) |
            clear_tiles.si(rasterlayer) |
            priority_group |
            high_level_group |
            drop_empty_tiles.si(rasterlayer) |
            send_success_signal.si(rasterlayer)
        )

        # Apply the parsing chain
        parsing_task_chain.apply_async()
    else:
        open_and_reproject_raster(rasterlayer)
        clear_tiles(rasterlayer)
        for zoom in zoom_range:
            create_tiles(rasterlayer, zoom)
        drop_empty_tiles(rasterlayer)
        send_success_signal(rasterlayer)
