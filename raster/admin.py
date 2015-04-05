from django.contrib import admin
from .models import RasterLayer, RasterLayerMetadata, RasterTile

# Register raster layer in admin
class RasterLayerModelAdmin(admin.ModelAdmin):
    readonly_fields = ('parse_log',)
    actions = ['reparse_rasters']

    def reparse_rasters(self, request, queryset):
        """
        Admin action to re-parse a set of rasterlayers.
        """
        for rasterlayer in queryset:
            rasterlayer.parse_log = ''
            rasterlayer.save()

        msg = 'Parsing Rasters, check parse logs for progress'
        self.message_user(request, msg)

admin.site.register(RasterLayer, RasterLayerModelAdmin)

# Register read-only raster metadata in admin
class RasterLayerMetadataModelAdmin(admin.ModelAdmin):
    readonly_fields = ('rasterlayer', 'uperleftx', 'uperlefty',
                       'width', 'height', 'scalex', 'scaley', 'skewx',
                       'skewy', 'numbands')
    def has_add_permission(self, request, obj=None):
        return False
    def has_delete_permission(self, request, obj=None):
        return False

admin.site.register(RasterLayerMetadata, RasterLayerMetadataModelAdmin)

# Register read-only raster tile in admin
class RasterTileModelAdmin(admin.ModelAdmin):
    readonly_fields = ('rast', 'rasterlayer', 'filename', 'is_base', 'tilex',
                       'tiley', 'tilez')
    def has_add_permission(self, request, obj=None):
        return False
    def has_delete_permission(self, request, obj=None):
        return False

admin.site.register(RasterTile, RasterTileModelAdmin)


from django.contrib import admin
from raster.models import LegendSemantics, LegendEntry, Legend

admin.site.register(LegendSemantics)
admin.site.register(LegendEntry)


class LegendEntriesInLine(admin.TabularInline):
    model = Legend.entries.through


class LegendAdmin(admin.ModelAdmin):
    inlines = (
        LegendEntriesInLine,
    )

admin.site.register(Legend, LegendAdmin)
