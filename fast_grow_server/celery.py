"""Initialization of the central celery app instance"""
import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fast_grow_server.settings')

app = Celery('fast_grow_server')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()


@app.task(bind=True)
def debug_task(self):
    """Standard debug task as per the celery docs"""
    print(f'Request: {self.request:0!r}')
