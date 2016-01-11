=====================
Parsing raster layers
=====================

How to input data.

After setting the package up, raster files can be uploaded through the admin interface using the RasterLayer model. Specify a layer name, the raster data type (continuous, categorical, mask or rank ordered), the raster's srid, the nodata value and the raster file to be uploaded.

Upon saving the a RasterLayer instance with a raster file, django-raster automatically loads the raster data from the file into a raster field in the RasterTile model. The RasterLayer instances have a *parse_log* field, which stores information about the parsing process. For debugging, there might be some useful information in the parse log.

A simple TMS view is part of this package as well, to serve the tiles with dynamic symbology. The endpoint is briefly described below, it works as a ``{z}/{x}/{y}.png`` url.
