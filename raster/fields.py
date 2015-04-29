from django.db import models
from raster.ogrraster import OGRRaster


class RasterField(models.Field):
    """
    Binary field that uses the raster db type to store raster data in django
    """

    description = "PostGIS Raster Field"

    __metaclass__ = models.SubfieldBase

    def __init__(self, srid=4326, **kwargs):
        self.srid = srid

        super(RasterField, self).__init__(**kwargs)

    def db_type(self, connection):
        return 'raster'

    def from_db_value(self, value, connection):
        # Convert PostGIS Raster string to OGR Rasters
        if value:
            value = OGRRaster(value)

        return value

    def get_prep_value(self, value):
        value = super(RasterField, self).get_prep_value(value)

        if value is None:
            return value
        elif isinstance(value, OGRRaster):
            return value.to_postgis_raster()
        elif isinstance(value, str):
            return value
        else:
            raise ValueError('Could not create raster from lookup value.')

    def to_python(self, value):
        if value is None:
            return value

        if isinstance(value, OGRRaster):
            return value

        return OGRRaster(value)
