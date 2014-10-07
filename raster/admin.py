from django.contrib import admin
from .models import RasterLayer, RasterTile

# Register raster layer in admin
class RasterLayerModelAdmin(admin.ModelAdmin):
    readonly_fields = ('parse_log',)
    actions = ['reparse_raster']

    def reparse_raster(self, request, queryset):
        """Admin action to re-parse a rasterlayer
        """
        if queryset.count() > 1:
            self.message_user(request,
                              'You can only parse one RasterLayer at a time.',
                              level=messages.ERROR)
        else:
            rasterlayer = queryset[0]
            rasterlayer.parse_log = ''
            rasterlayer.save()
            msg = 'Parsing Raster, check parse log for progress'
            self.message_user(request, msg)

admin.site.register(RasterLayer, RasterLayerModelAdmin)

# Register read-only raster tile in admin
class RasterTileModelAdmin(admin.ModelAdmin):
    readonly_fields = ('rast', 'rasterlayer', 'filename', 'level')
    def has_add_permission(self, request, obj=None):
        return False
    def has_delete_permission(self, request, obj=None):
        return False

admin.site.register(RasterTile, RasterTileModelAdmin)
