import os, tempfile, shutil, subprocess, datetime

from django.db import connection

from raster.models import RasterTile

def parse_raster_layer(rasterlayer):
    """
    This function pushes the raster data from the Raster Layer into the
    RasterTile table, in tiles of 100x100 pixels.
    """
    # Clean previous parse log
    now = '[{0}] '.format(datetime.datetime.now().strftime('%Y-%m-%d %T'))
    rasterlayer.parse_log = now + 'Started parsing raster file\n'
    rasterlayer.save()

    # Create tempdir for raster file and get raster file name
    tmpdir = tempfile.mkdtemp()
    rastername = os.path.basename(rasterlayer.rasterfile.name)

    # Access rasterfile and store locally
    try:
        f = open(os.path.join(tmpdir, rastername), 'wb')
        for chunk in rasterlayer.rasterfile.chunks():
            f.write(chunk)
        f.close()
    except:
        rasterlayer.parse_log += 'Error: Library error for download\n'
        rasterlayer.save()
        shutil.rmtree(tmpdir)
        return

    # Setup import raster command pattern
    raster2pgsql = 'raster2pgsql -a -F -M -P -t 100x100 -s {srid} -N {nodata} {raster} '\
               'raster_rastertile > raster.sql'

    # Replace placeholders with current values
    raster2pgsql = raster2pgsql.format(srid=rasterlayer.srid, nodata=rasterlayer.nodata,
                                            raster=rastername)

    # Call raster2pgsql to setup sql file
    try:
        os.chdir(tmpdir)
        subprocess.call(raster2pgsql, shell=True)
    except:
        shutil.rmtree(tmpdir)
        rasterlayer.parse_log += 'Error: Failed to import raster data from file\n'
        rasterlayer.save()
        return

    # Remove existing tiles for this layer before loading new ones
    rasterlayer.rastertile_set.all().delete()

    # Drop current raster constraints before adding more data
    cursor = connection.cursor()
    cursor.execute("SELECT DropRasterConstraints('raster_rastertile'::name,'rast'::name)");

    # Insert raster data from file
    counter = 0
    for line in open(os.path.join(tmpdir, 'raster.sql')):
        if line in ['BEGIN;', 'END;']: continue
        cursor.execute(line)
        counter +=1
        if counter%500 == 0:
            rasterlayer.parse_log += "Processed {0} lines \n".format(counter)

    # Set raster constraints
    cursor.execute("SELECT AddRasterConstraints('raster_rastertile'::name,'rast'::name)");

    # Set foreign key in new raster tiles
    RasterTile.objects.filter(filename=rastername)\
            .update(rasterlayer=rasterlayer.id)

    # Vacuum table
    cursor.execute('VACUUM ANALYZE "raster_rastertile"')

    # Finish message in parse log and save
    now = '[{0}] '.format(datetime.datetime.now().strftime('%Y-%m-%d %T'))
    rasterlayer.parse_log += now + 'Finished parsing patch collection'
    rasterlayer.save()

    # Remove tempdir with source file
    shutil.rmtree(tmpdir)
