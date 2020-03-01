from django.contrib.gis.db import models


class RasterFieldModel(models.Model):
    rast = models.RasterField()

    def __str__(self):
        return str(self.id)
