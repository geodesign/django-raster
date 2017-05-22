django-raster change log
========================

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
