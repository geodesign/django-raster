import shutil
import traceback

from celery import group, shared_task

from django.conf import settings
from raster.tiles.const import GLOBAL_MAX_ZOOM_LEVEL, MIN_ZOOMLEVEL_TASK_PARALLEL
from raster.tiles.parser import RasterLayerParser


@shared_task
def create_tiles(rasterlayer_id, zoom, extract_metadata=False):
    """
    Create all tiles for a raster layer at the input zoom level.
    """
    try:
        parser = RasterLayerParser(rasterlayer_id)

        # Open raster file and extract metadata if requested.
        if extract_metadata:
            parser.open_raster_file()
            parser.extract_metadata()

        # Check if zoom level should be built.
        if zoom is None:
            zoom = parser.max_zoom
        elif isinstance(zoom, (int, float)):
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
            tmpdir = parser.tmpdir
            parser.dataset = None
            parser = None
            shutil.rmtree(tmpdir)


@shared_task
def clear_tiles(rasterlayer_id):
    """
    Drop all tiles of a rasterlayer.
    """
    parser = RasterLayerParser(rasterlayer_id)
    parser.drop_all_tiles()


@shared_task
def send_success_signal(rasterlayer_id):
    """
    Drop empty tiles of a raster layer and send parse succes signal.
    """
    parser = RasterLayerParser(rasterlayer_id)
    parser.send_success_signal()


@shared_task
def all_in_one(rasterlayer_id, zoom_range):
    """
    Parses raster in a single task.
    """
    clear_tiles(rasterlayer_id)
    create_tiles(rasterlayer_id, zoom_range, True)
    send_success_signal(rasterlayer_id)


def parse(rasterlayer_id):
    """
    Parse raster layer to extract metadata and create tiles.
    """
    parser = RasterLayerParser(rasterlayer_id)
    parser.log('Started parsing raster.')

    # Create array of all allowed zoom levels
    if parser.rasterlayer.build_pyramid:
        zoom_range = list(range(GLOBAL_MAX_ZOOM_LEVEL + 1))
    else:
        if parser.rasterlayer.max_zoom is not None:
            zoom_range = (parser.rasterlayer.max_zoom, )
        else:
            zoom_range = None

    # Check if parsing should happen asynchronously
    parse_async = getattr(settings, 'RASTER_USE_CELERY', False)
    parse_single_task = getattr(settings, 'RASTER_PARSE_SINGLE_TASK', False)
    if parse_async and not parse_single_task:
        if zoom_range is not None:
            # Bundle the first five raster layers to one task. For low zoom
            # levels, downloading is more costly than parsing.
            create_tiles_chain = create_tiles.si(rasterlayer_id, zoom_range[:MIN_ZOOMLEVEL_TASK_PARALLEL], True)

            # Run the higher level zooms in parallel tasks through a task group.
            if len(zoom_range) > MIN_ZOOMLEVEL_TASK_PARALLEL:
                high_zoom_level_group = group(
                    create_tiles.si(rasterlayer_id, zoom) for zoom in zoom_range[MIN_ZOOMLEVEL_TASK_PARALLEL:]
                )
                # Combine bundle and middle levels to priority group.
                create_tiles_chain = (create_tiles_chain | high_zoom_level_group)

        else:
            create_tiles_chain = create_tiles.si(rasterlayer_id, None, True)

        # Setup the parser logic as parsing chain
        parsing_task_chain = (
            clear_tiles.si(rasterlayer_id)
            | create_tiles_chain
            | send_success_signal.si(rasterlayer_id)
        )

        # Apply the parsing chain
        parser.log('Parse task queued, waiting for worker availability.')
        parsing_task_chain.apply_async()
    elif parse_async and parse_single_task:
        parser.log('Parse task queued in all-in-one mode, waiting for worker availability.')
        all_in_one.delay(rasterlayer_id, zoom_range)
    else:
        all_in_one(rasterlayer_id, zoom_range)
