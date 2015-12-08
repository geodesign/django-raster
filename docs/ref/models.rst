======
Models
======

Legend Objects
--------------
To render XYZ tiles through the TMS view, a colormap or legend has to be created. A ``Legend`` object basically consists of a many-to-many field to ``LegendEntries``, which in turn define the expression used to filter pixels, a color and a foreign key to a ``LegendSemantics`` object. The LegendSemantics object defines the name, it is separated from the LegendEntry to be able to directly associate the semantics of pixel values from several different raster layers for analysis.

An example to create a Legend object with one LegendEntry is shown in the following snippet::

        >>> from raster.models import LegendSemantics, LegendEntry, Legend
        >>> semantics = LegendSemantics.objects.create(name='Earth')
        >>> entry = LegendEntry.objects.create(semantics=semantics, expression='1', color='#FFFFFF')
        >>> legend = Legend.objects.create(title='MyLegend')
        >>> legend.entries.add(entry)
        >>> legend.json
        ... '[{"color": "#FFFFFF", "expression": "1", "name": "Earth"}]'

.. class:: Legend

.. class:: LegendEntry

.. class:: LegendSemantics


Compression
-----------
By default all rasters are compressed during parsing using LZW compression. This potentially saves a lot of storage space for large rasters,
but might slow down the parsing process due to the compression overhead. The compress method can be changed using the ``RASTER_COMPRESS_METHOD`` setting.
Allowed options are ``JPEG``, ``LZW``, ``PACKBITS``,  ``DEFLATE``, ``CCITTRLE``,  ``CCITTFAX3``, ``CCITTFAX4``, ``LZMA``. To disable compression, specify this setting as an empty string ``''``.
