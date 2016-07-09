from __future__ import unicode_literals

from raster.utils import colormap_to_rgba


def set_session_colormap(session, key, colormap):
    """
    Store the colormap in the user session.
    """
    raster_legends = session.get('raster_legends', {})
    raster_legends[key] = {
        "colormap": colormap_to_rgba(colormap),
    }

    session['raster_legends'] = raster_legends


def get_session_colormap(session, key):
    """
    Get the colormap form a legend stored in the user session and identified
    by key.
    """
    raster_legends = session.get('raster_legends', {})
    legend = raster_legends.get(key)
    if legend:
        return legend['colormap']
