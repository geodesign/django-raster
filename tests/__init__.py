try:
    import os
    import sys

    from celery import Celery

    from django.conf import settings

    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'example.settings')

    sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

    APP = Celery('example')

    APP.config_from_object('django.conf:settings')
    APP.autodiscover_tasks(lambda: settings.INSTALLED_APPS)

except ImportError:
    pass
