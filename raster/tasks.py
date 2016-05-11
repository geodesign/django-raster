from __future__ import unicode_literals

import shutil
import traceback

from celery import group, task

from django.conf import settings
from raster.tiles.const import GLOBAL_MAX_ZOOM_LEVEL
from raster.tiles.parser import RasterLayerParser


@task
def create_tiles(rasterlayer, zoom, extract_metadata=False):
    """
    Create all tiles for a raster layer at the input zoom level.
    """
    try:
        parser = RasterLayerParser(rasterlayer)

        # Open raster file and extract metadata if requested.
        if extract_metadata:
            parser.open_raster_file()
            parser.extract_metadata()

        # Check if zoom level should be built.
        if isinstance(zoom, (int, float)):
            if zoom > parser.max_zoom:
                return
        else:
            zoom = [zl for zl in zoom if zl <= parser.max_zoom]
            if not len(zoom):
                return
        # Open raster file if not open already.
        if not extract_metadata:
            parser.open_raster_file()

        parser.reproject_rasterfile()
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
def send_success_signal(rasterlayer):
    """
    Drop empty tiles of a raster layer and send parse succes signal.
    """
    parser = RasterLayerParser(rasterlayer)
    parser.drop_empty_tiles()
    parser.send_success_signal()


def parse(rasterlayer):
    """
    Parse raster layer to extract metadata and create tiles.
    """
    parser = RasterLayerParser(rasterlayer)
    parser.log('Started parsing raster.')

    # Create array of all allowed zoom levels
    if rasterlayer.build_pyramid:
        zoom_range = range(GLOBAL_MAX_ZOOM_LEVEL + 1)
    else:
        if rasterlayer.max_zoom is not None:
            zoom_range = (rasterlayer.max_zoom, )
        elif hasattr(rasterlayer, 'metadata') and rasterlayer.metadata.max_zoom is not None:
            zoom_range = (rasterlayer.metadata.max_zoom, )
        else:
            parser.log('Could not determine max zoom level, aborting prasing.')
            return

    # Check if parsing should happen asynchronously
    async = getattr(settings, 'RASTER_USE_CELERY', False)

    if async:
        # Bundle the first five raster layers to one task. For low zoom
        # levels, downloading is more costly than parsing.
        create_tiles_chain = create_tiles.si(rasterlayer, zoom_range[:5], True)

        if len(zoom_range) > 5:
            # Create a group of tasks with the middle zoom levels that are
            # prioritized over high zoom levels.
            middle_level_group = group(
                create_tiles.si(rasterlayer, zoom) for zoom in zoom_range[5:10]
            )
            # Combine bundle and middle levels to priority group.
            create_tiles_chain = group(create_tiles_chain, middle_level_group)

        if len(zoom_range) > 10:
            # Create a task group for high zoom levels.
            high_level_group = group(create_tiles.si(rasterlayer, zoom) for zoom in zoom_range[10:])
            create_tiles_chain = (create_tiles_chain | high_level_group)

        # Setup the parser logic as parsing chain
        parsing_task_chain = (
            clear_tiles.si(rasterlayer) |
            create_tiles_chain |
            send_success_signal.si(rasterlayer)
        )

        # Apply the parsing chain
        parser.log('Parse task queued, waiting for worker availability.')
        parsing_task_chain.apply_async()
    else:
        clear_tiles(rasterlayer)
        create_tiles(rasterlayer, zoom_range, True)
        send_success_signal(rasterlayer)
