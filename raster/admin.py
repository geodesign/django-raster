from django.contrib import admin
from .models import RasterLayer, RasterTile

# Register raster layer in admin
class RasterLayerModelAdmin(admin.ModelAdmin):
    readonly_fields = ('parse_log',)

admin.site.register(RasterLayer, RasterLayerModelAdmin)

# Register read-only raster tile in admin
class RasterTileModelAdmin(admin.ModelAdmin):
    readonly_fields = ('rast', 'rasterlayer', 'filename')
    def has_add_permission(self, request, obj=None):
        return False
    def has_delete_permission(self, request, obj=None):
        return False

admin.site.register(RasterTile, RasterTileModelAdmin)
