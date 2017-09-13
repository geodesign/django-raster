django-raster change log
========================

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
