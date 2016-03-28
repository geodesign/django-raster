===============
Rendering tiles
===============
After creating a :class:`RaterLayer` through the admin, the tiles for that
layer can be accessed through the tiles url. The raster urls have to be added
to the application's url patterns. Here we assume that the `/raster/` base url
is used as proposed in the :doc:`installation` section.

The tiles url is structured as follows,

::

    /raster/tiles/layer_id/{z}/{x}/{y}.png

where the ``layer_id`` is the primary key of a raster layer. This structure can be
used direclty in online mapping software such as `OpenLayers`__ or `Leaflet`__. An
example request could look like this: ``/raster/tiles/23/8/536/143.png``,
returning a tile in png format of the layer with ID ``pk=23`` at zoom level
``z=8`` and indexes ``x=536`` and ``y=143``.

__ http://openlayers.org/
__ http://leafletjs.com/

By default, the tiles are rendered using simple grayscale. legend used for the layer. However, the
symbology can be changed by assigning a :class:`Legend` to the layer.

Legends
-------
Legends are objects that are used to interpret raster data. This includes
the cartographic information (colors), but also the semantics of the data
(such as names). This information can be input through the admin interface.

A legend is stored as in the :class:`Legend` model, which is essentially a
collection of :class:`LegendEntries` that each have an expression for
classifying the data and a semantic meaning of the expression. The semantics
of the expression are stored in the :class:`LegendSemantics` model. Here is
an example for a legend representing two temperatures::

    >>> from raster.models import Legend, LegendEntry, LegendSemantics
    >>> hot_semantics = LegendSemantics.objects.create(name='Hot')
    >>> cold_semantics = LegendSemantics.objects.create(name='Cold')
    >>> hot_entry = LegendEntry.objects.create(semantics=cold, expression='0', color='#0000FF')
    >>> cold_entry = LegendEntry.objects.create(semantics=hot, expression='1', color='#FF0000')
    >>> legend = Legend.objects.create(title='Temperatures')
    >>> legend.entries.add(entry)
    >>> legend.json
    ... '[{"color": "#FFFFFF", "expression": "1", "name": "Earth"}]'

The classification expression describes a section of the pixel values in the
data. It is either an exact number for discrete rasters, or a formula for
continuous rasters.


:class:`Legend` objects are sets of cartographies that are used to interpret
raster data in django-raster. The are composed of a set of
:class:`LegendEntries` which in turn each have a :class:`LegendSemantics`
attribute.
