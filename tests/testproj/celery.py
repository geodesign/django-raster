from __future__ import absolute_import, unicode_literals

import os
import sys

from celery import Celery

from django.conf import settings

# Add the apps directory to the python path for celery to find the apps
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '../..'))

# set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tests.testproj.settings')

app = Celery('tests.testproj')

app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django app configs.
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)


@app.task(bind=True)
def debug_task(self):
    print('Request: {0!r}'.format(self.request))
