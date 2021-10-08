from django import forms
from django.contrib import admin, messages
from django.http import HttpResponseRedirect
from django.shortcuts import render

from .models import (
    Legend, LegendEntry, LegendSemantics, RasterProduct, RasterLayer, RasterLayerBandMetadata, RasterLayerMetadata,
    RasterLayerParseStatus, RasterLayerReprojected, RasterTile
)


class FilenameActionForm(forms.Form):
    """
    Form for changing the filename of a raster.
    """
    _selected_action = forms.CharField(widget=forms.MultipleHiddenInput)
    path = forms.CharField(label='Filepath', required=False)


class RasterLayerMetadataInline(admin.TabularInline):
    model = RasterLayerMetadata
    extra = 0
    readonly_fields = (
        'srid', 'uperleftx', 'uperlefty', 'width', 'height',
        'scalex', 'scaley', 'skewx', 'skewy', 'numbands',
        'max_zoom', 'srs_wkt',
    )

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class RasterLayerParseStatusInline(admin.TabularInline):
    model = RasterLayerParseStatus
    extra = 0
    readonly_fields = ('status', 'tile_levels', 'log', )

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class RasterLayerBandMetadataInline(admin.TabularInline):
    model = RasterLayerBandMetadata
    extra = 0
    readonly_fields = (
        'band', 'nodata_value', 'max', 'min', 'std', 'mean',
        'hist_values', 'hist_bins',
    )

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class RasterLayerReprojectedInline(admin.TabularInline):
    model = RasterLayerReprojected
    readonly_fields = (
        'rasterlayer', 'rasterfile',
    )
    extra = 0

    def has_add_permission(self, request, obj=None):
        return False

class RasterProductModelAdmin(admin.ModelAdmin):
    list_display = ('name',)

class RasterLayerModelAdmin(admin.ModelAdmin):
    """
    Admin action to update filepaths only. Files can be uploadded to the
    filesystems through any channel and then files can be assigned to the
    raster objects through this action. This might be useful for large raster
    files.
    """
    actions = ['reparse_rasters']
    list_filter = ('datatype', 'parsestatus__status')
    search_fields = ('name', 'rasterfile')
    inlines = (
        RasterLayerParseStatusInline,
        RasterLayerMetadataInline,
        RasterLayerBandMetadataInline,
        RasterLayerReprojectedInline,
    )

    def reparse_rasters(self, request, queryset):
        """
        Admin action to re-parse a set of rasterlayers.
        """
        for rasterlayer in queryset:
            rasterlayer.parsestatus.reset()
            rasterlayer.refresh_from_db()
            rasterlayer.save()
        msg = 'Parsing Rasters, check parse logs for progress'
        self.message_user(request, msg)

class RasterLayerMetadataModelAdmin(admin.ModelAdmin):
    readonly_fields = (
        'rasterlayer', 'uperleftx', 'uperlefty', 'width', 'height',
        'scalex', 'scaley', 'skewx', 'skewy', 'numbands', 'srid', 'srs_wkt',
    )

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class RasterTileModelAdmin(admin.ModelAdmin):
    readonly_fields = (
        'rast', 'rasterlayer', 'tilex', 'tiley', 'tilez',
    )

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class LegendEntriesInLine(admin.TabularInline):
    model = LegendEntry
    extra = 0


class LegendAdmin(admin.ModelAdmin):
    inlines = (
        LegendEntriesInLine,
    )


admin.site.register(LegendSemantics)
admin.site.register(RasterProduct, RasterProductModelAdmin)
admin.site.register(RasterLayer, RasterLayerModelAdmin)
admin.site.register(RasterTile, RasterTileModelAdmin)
admin.site.register(RasterLayerMetadata, RasterLayerMetadataModelAdmin)
admin.site.register(LegendEntry)
admin.site.register(Legend, LegendAdmin)
