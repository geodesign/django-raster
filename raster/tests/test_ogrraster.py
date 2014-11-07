import numpy
from osgeo import osr, gdal, gdalconst

from django.test import TestCase

from raster.ogrraster import OGRRaster
from raster.fields import RasterField

from .models import RasterFieldModel


class RasterFieldTest(TestCase):

    def setUp(self):
        # Create gdal in-memory raster
        driver = gdal.GetDriverByName('MEM')
        raster = driver.Create('OGRRaster', 2, 3, 2, gdalconst.GDT_Byte)
        
        srs = osr.SpatialReference()
        srs.ImportFromEPSG(4326)
        raster.SetProjection(srs.ExportToWkt())

        raster.SetGeoTransform(( -0.1, -0.2, 0.3, 0.4, 0.5, 0.6))

        band1 = raster.GetRasterBand(1)
        band1.SetNoDataValue(1)
        data1 = numpy.array([1,1,2,2,3,3]).reshape(3, 2)
        band1.WriteArray(data1)

        band2 = raster.GetRasterBand(2)
        band2.SetNoDataValue(2)
        data2 = numpy.array([4,4,5,5,6,6]).reshape(3, 2)
        band2.WriteArray(data2)

        self.d = RasterFieldModel.objects.create(rast=raster)

    def test_object_creation(self):
        self.assertIsInstance(self.d.rast, OGRRaster)

    def test_srid(self):
        self.assertEqual(self.d.rast.srid, 4326)

    def test_value_count(self):
        self.assertTrue(numpy.array_equal(
            self.d.rast.value_count, numpy.array([[1,2],[2,2],[3,2]])))

    def test_metadata(self):
        self.assertEqual(self.d.rast.metadata, {
            'upperleftx': -0.1,
            'upperlefty': 0.4,
            'scalex': -0.2,
            'scaley': 0.6,
            'skewx': 0.3,
            'skewy': 0.5
        })
