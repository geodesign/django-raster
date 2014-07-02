# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'RasterLayer.nodata'
        db.add_column(u'raster_rasterlayer', 'nodata',
                      self.gf('django.db.models.fields.CharField')(default='-9999', max_length=100),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'RasterLayer.nodata'
        db.delete_column(u'raster_rasterlayer', 'nodata')


    models = {
        u'raster.rasterlayer': {
            'Meta': {'object_name': 'RasterLayer'},
            'datatype': ('django.db.models.fields.CharField', [], {'default': "'co'", 'max_length': '2'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'nodata': ('django.db.models.fields.CharField', [], {'default': "'-9999'", 'max_length': '100'}),
            'parse_log': ('django.db.models.fields.TextField', [], {'default': "''", 'null': 'True', 'blank': 'True'}),
            'rasterfile': ('django.db.models.fields.files.FileField', [], {'max_length': '100'}),
            'srid': ('django.db.models.fields.CharField', [], {'default': "'3086'", 'max_length': '10'})
        },
        u'raster.rastertile': {
            'Meta': {'object_name': 'RasterTile'},
            'filename': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'rast': ('raster.fields.RasterField', [], {'null': 'True', 'blank': 'True'}),
            'rasterlayer': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['raster.RasterLayer']", 'null': 'True', 'blank': 'True'}),
            'rid': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        }
    }

    complete_apps = ['raster']