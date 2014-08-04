from django.contrib import admin
from .models import RasterLayer

class RasterLayerModelAdmin(admin.ModelAdmin):
    readonly_fields=('parse_log',)

# Register raster layer in admin
admin.site.register(RasterLayer, RasterLayerModelAdmin)
