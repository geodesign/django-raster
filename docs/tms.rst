===============
Rendering tiles
===============
After adding some data through the admin, the resulting tiles can be accessed
through the tiles url. The url is structured as follows::

    /raster/tiles/layer_id/{z}/{x}/{y}.png

Where the layer_id is the primary key of a raster layer. This structure can be
used direclty in online mapping software such as OpenLayers or Leaflet. An
example request could look like this: ``/raster/tiles/23/8/536/143.png``,
returning a tile in png format of the layer with ID ``pk=23`` at zoom level
``z=8`` and indexes ``x=536`` and ``y=143``.

Tiles are served with dynamic symbology using Legend objects.
