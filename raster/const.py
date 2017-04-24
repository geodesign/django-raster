from __future__ import unicode_literals

IMG_FORMATS = {'png': ('PNG', 'image/png'), 'jpg': ('JPEG', 'image/jpeg')}
EXPORT_MAX_PIXELS = 10000 * 10000
MAX_EXPORT_NAME_LENGTH = 100
README_TEMPLATE = """Django Raster Algebra Export
============================
{description}
Input layers
------------
{layers}
Raster algebra formula
----------------------
{formula}

Geographic parameters
---------------------
Zoom level: {zoom}
Tile index range x: {xindexrange}
Tile index range y: {yindexrange}
Bounding-box: {bbox}

Source
------
Files auto-generated on {datetime} from the following url:

{url}
"""
