from django.db import models
from south.modelsinspector import add_introspection_rules

class RasterField(models.BinaryField):
    """
    Binary field that uses the raster db type to store raster data in django
    """
    def db_type(self, connection):
        return 'raster'

add_introspection_rules([], ["^raster\.fields\.RasterField"])
