from abc import abstractmethod
from django.db import models
from django.db.models import QuerySet
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from grit.auth.models import CustomUser


class ScopedManager(models.Manager):
    def for_user(self, user) -> QuerySet:
        from grit.auth.models import CustomUser
        try:
            if user.is_superuser:
                return super().get_queryset()
            return self.get_queryset().filter(owner=user)
        except CustomUser.DoesNotExist:
            return super().get_queryset().none()
