from django.contrib import admin
from .models import RasterLayer, RasterTile

class RasterLayerModelAdmin(admin.ModelAdmin):
    
    actions = ['parse_raster_layer_data']

    def parse_raster_layer_data(self, request, queryset):
        # Send parse data command to celery
        for lyr in queryset:
            lyr.parse()

        # Message user 
        self.message_user(request, 
            "Parsing raster, please check the parse log for status(es)")

# Register models in admin
admin.site.register(RasterLayer, RasterLayerModelAdmin)
admin.site.register(RasterTile)
