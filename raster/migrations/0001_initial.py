# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'RasterLayer'
        db.create_table(u'raster_rasterlayer', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=100, null=True, blank=True)),
            ('description', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('datatype', self.gf('django.db.models.fields.CharField')(default='co', max_length=2)),
            ('rasterfile', self.gf('django.db.models.fields.files.FileField')(max_length=100)),
            ('srid', self.gf('django.db.models.fields.CharField')(default='3086', max_length=10)),
            ('parse_log', self.gf('django.db.models.fields.TextField')(default='', null=True, blank=True)),
        ))
        db.send_create_signal(u'raster', ['RasterLayer'])

        # Adding model 'RasterTile'
        db.create_table(u'raster_rastertile', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('rast', self.gf('raster.fields.RasterField')(null=True, blank=True)),
            ('rasterlayer', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['raster.RasterLayer'], null=True, blank=True)),
            ('filename', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
        ))
        db.send_create_signal(u'raster', ['RasterTile'])


    def backwards(self, orm):
        # Deleting model 'RasterLayer'
        db.delete_table(u'raster_rasterlayer')

        # Deleting model 'RasterTile'
        db.delete_table(u'raster_rastertile')


    models = {
        u'raster.rasterlayer': {
            'Meta': {'object_name': 'RasterLayer'},
            'datatype': ('django.db.models.fields.CharField', [], {'default': "'co'", 'max_length': '2'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'parse_log': ('django.db.models.fields.TextField', [], {'default': "''", 'null': 'True', 'blank': 'True'}),
            'rasterfile': ('django.db.models.fields.files.FileField', [], {'max_length': '100'}),
            'srid': ('django.db.models.fields.CharField', [], {'default': "'3086'", 'max_length': '10'})
        },
        u'raster.rastertile': {
            'Meta': {'object_name': 'RasterTile'},
            'filename': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'rast': ('raster.fields.RasterField', [], {'null': 'True', 'blank': 'True'}),
            'rasterlayer': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['raster.RasterLayer']", 'null': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['raster']