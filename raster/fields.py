from django.contrib.gis.gdal import GDALRaster
from django.db.models import FileField
from django.db.models.fields.files import FieldFile


class RasterFile(FieldFile, GDALRaster):
    """
    A FieldFile with a raster attribute.
    """

    def __init__(self, *args, **kwargs):
        super(RasterFile, self).__init__(*args, **kwargs)

        try:
            GDALRaster.__init__(self, self.file)
        except:
            pass

    _name = ''

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, value):
        self._name = value


class RasterFileField(FileField):
    """
    A file based raster field.
    """
    attr_class = RasterFile
