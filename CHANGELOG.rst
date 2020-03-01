django-raster change log
========================

0.8
---
* Django 3.0 compatability.

0.7
---
* Fixed array field default.
* Fixed tms endpoint for tif format requests of empty tiles.

0.6
---
* BREAKING CHANGE: Dropped support for Python 2.

* Changed alpha channel handling on RGB endpoint. The alpha channel is now
  switched off by default. To activate it, add the ``alpha`` query parameter
  to the rgb request.

* Added enhancers from the ``PIL.ImageEnhance`` to the tiles endpoints. Tiles
  can now be enhanced dynamically.

* The RGB endpoint now supports the band accessor syntax similar to the
  regular algebra endpoint.

* Single pixel value lookups by coordinates from algebra expressions can now be
  requested.

* Added option to add direct s3 links that download data from s3 using boto3.
  This allows specifying private or requester-pays buckets as raster source.

* Made it possible to request TIFF tiles on the TMS, Algebra and RGB endpoints.

* Updated dependency versions to latest respective releases.

0.5
---
* Added ``memory_efficient`` flag to value count aggregator. The value counts
  are now computed after collecting the complete array of data for the value
  count area. This might require a lot of memory, a tile-by-tile based
  computation can be activated with this flag.

* Fixed bug when computing continuous histograms over multiple tiles. The
  histogram now has consistent breaks.

* A histogram breaks range can now be specified on the value count aggregation.

0.4
---

* Fixed bug for nodata None on the raster algebra parser.
  See https://github.com/geodesign/django-raster/issues/20.

* Changed raster legend related model structure. The new
  structure has direct foreign keys from the legend entry to the legend. This
  removes the need for an intermediate through table.

* Unified the TMS and the Algebra Views into one single view.

* Simplified the url structure, the format type keyword now does not
  include the "." anymore.

* Celery 4.0 is now a requirement.
