import uuid
from django.db import models
from core.managers import ScopedManager
from customauth.models import CustomUser


class BaseModel(models.Model):
    id = models.UUIDField(default=uuid.uuid4, unique=True, primary_key=True)
    metadata = models.JSONField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    owner = models.ForeignKey(CustomUser, on_delete=models.DO_NOTHING, blank=True, null=True)

    # Managers
    objects = models.Manager()  # Default manager
    scoped = ScopedManager()

    class Meta:
        abstract = True