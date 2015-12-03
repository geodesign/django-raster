from django.core.exceptions import SuspiciousOperation


class RasterException(SuspiciousOperation):
    """Something raster related went wrong."""


class RasterAlgebraException(SuspiciousOperation):
    """Raster Algebra Evaluation Failed."""
