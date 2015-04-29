"""
Model for testing raster field.
"""
from django.db import models
from raster.fields import RasterField


class RasterFieldModel(models.Model):
    rast = RasterField()

    def __str__(self):
        return str(self.id)
