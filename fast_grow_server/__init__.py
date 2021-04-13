"""Loads the celery app any time fast_grow_server is imported"""
from .celery import app as celery_app

__all__ = ('celery_app',)
