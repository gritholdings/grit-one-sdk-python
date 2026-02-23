from django.db import models
from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from .base import BaseModel
APP_METADATA_SETTINGS = getattr(settings, 'APP_METADATA_SETTINGS', {})


def get_task_status_choices():
    statuses = APP_METADATA_SETTINGS.get('CHOICES', {}).get('task_status', {})
    return [(key, value['label']) for key, value in statuses.items()]


def get_default_task_status():
    statuses = APP_METADATA_SETTINGS.get('CHOICES', {}).get('task_status', {})
    if statuses:
        return next(iter(statuses.keys()))
    return None


def get_resolution_choices():
    resolutions = APP_METADATA_SETTINGS.get('CHOICES', {}).get('resolutions', {})
    return [(key, value['label']) for key, value in resolutions.items()]


class Task(BaseModel):
    what_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    what_id = models.UUIDField()
    what = GenericForeignKey('what_type', 'what_id')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    status = models.CharField(
        max_length=255,
        choices=get_task_status_choices(),
        default=get_default_task_status()
    )
    resolution = models.CharField(
        max_length=255,
        choices=get_resolution_choices(),
        blank=True
    )
    due_datetime = models.DateTimeField(blank=True, null=True)
    def __str__(self):
        return self.title
