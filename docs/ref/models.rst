======
Models
======

RasterLayers
------------
Representation of raster files.

.. class:: RasterLayer

.. class:: RasterTile

Legend Objects
--------------
To render XYZ tiles through the TMS view, a colormap or legend has to be created. A ``Legend`` object basically consists of a many-to-many field to ``LegendEntries``, which in turn define the expression used to filter pixels, a color and a foreign key to a ``LegendSemantics`` object. The LegendSemantics object defines the name, it is separated from the LegendEntry to be able to directly associate the semantics of pixel values from several different raster layers for analysis.

An example to create a Legend object with one LegendEntry is shown in the following snippet::

        >>> from raster.models import LegendSemantics, LegendEntry, Legend
        >>> hot = LegendSemantics.objects.create(name='Hot')
        >>> cold = LegendSemantics.objects.create(name='Cold')
        >>> entry = LegendEntry.objects.create(semantics=hot, expression='1', color='#FF0000')
        >>> entry = LegendEntry.objects.create(semantics=cold, expression='0', color='#0000FF')
        >>> legend = Legend.objects.create(title='MyLegend')
        >>> legend.entries.add(entry)
        >>> legend.json
        ... '[{"color": "#FFFFFF", "expression": "1", "name": "Earth"}]'

.. class:: Legend

.. class:: LegendEntry

.. class:: LegendSemantics
