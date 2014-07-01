import os, tempfile, shutil, requests, subprocess, datetime

from celery.contrib.methods import task

from django.db import models, connection

from .fields import RasterField

class RasterLayer(models.Model):
    """Source data model for raster layers"""

    DATATYPES = (('co', 'Continuous'), ('ca', 'Categorical'),
                ('ma', 'Mask'), ('ro', 'Rank Ordered'))

    name = models.CharField(max_length = 100, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    datatype = models.CharField(max_length = 2, choices = DATATYPES,
        default='co')
    rasterfile = models.FileField(upload_to='rasters')
    srid = models.CharField(max_length=10, default='3086')
    parse_log = models.TextField(blank=True, null=True, default='')

    def __unicode__(self):
        return '{name}'.format(name=self.name)

    @task()
    def parse(self):
        """
        This method pushes the raster data from the Raster Layer into the
        RasterTile table, in tiles of 100x100 pixels.

        ToDo: Make the tile size a setting.
        """

        # Clean previous parse log
        now = '[{0}] '.format(datetime.datetime.now().strftime('%Y-%m-%d %T'))
        self.parse_log = now + 'Started parsing raster file\n'
        self.save()

        # Create tempdir for raster file and get raster file name
        tmpdir = tempfile.mkdtemp()
        rastername = os.path.basename(self.rasterfile.name)

        # Access rasterfile and store locally
        try:
            f = open(os.path.join(tmpdir, rastername), 'wb')
            for chunk in self.rasterfile.chunks():
                f.write(chunk)
            f.close()
        except:
            self.parse_log += 'Error: Library error for download\n'
            self.save()
            shutil.rmtree(tmpdir)
            return

        # Setup import raster command pattern
        raster2pgsql = 'raster2pgsql -a -F -M -C -t 100x100 -s {srid} {raster} '\
                   'raster_rastertile > raster.sql'

        # Replace placeholders with current values
        raster2pgsql = raster2pgsql.format(srid=self.srid, raster=rastername)

        # Call raster2pgsql to setup sql file
        try:
            os.chdir(tmpdir)
            subprocess.call(raster2pgsql, shell=True)
        except:
            shutil.rmtree(tmpdir)
            self.parse_log += 'Error: Failed to import raster data from file\n'
            self.save()
            return

        # Remove existing tiles for this layer before loading new ones
        self.rastertile_set.all().delete()

        # Setup cursor and insert raster data from file
        cursor = connection.cursor()
        counter = 0
        for line in open(os.path.join(tmpdir, 'raster.sql')):
            if line in ['BEGIN;', 'END;']: continue
            cursor.execute(line)
            counter +=1
            if counter%500 == 0:
                self.parse_log += "Processed {0} lines \n".format(counter)

        # Vacuum table
        cursor.execute('VACUUM ANALYZE "raster_rastertile"')

        # Set foreign key in new raster tiles
        RasterTile.objects.filter(filename=rastername)\
                .update(rasterlayer=self.id)

        # Vacum analyze raster table
        cursor.execute('VACUUM ANALYZE "raster_rastertile"')

        # Finish message in parse log and save
        now = '[{0}] '.format(datetime.datetime.now().strftime('%Y-%m-%d %T'))
        self.parse_log += now + 'Finished parsing patch collection'
        self.save()

        # Remove tempdir with source file
        shutil.rmtree(tmpdir)

class RasterTile(models.Model):
    """Model to store individual tiles of a raster data source layer"""
    rid = models.AutoField(primary_key=True)
    rast = RasterField(null=True, blank=True)
    rasterlayer = models.ForeignKey(RasterLayer, null=True, blank=True)
    filename = models.TextField(null=True, blank=True)
