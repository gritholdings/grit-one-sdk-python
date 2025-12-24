from abc import abstractmethod
from django.db import models
from django.db.models import QuerySet
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from grit.auth.models import CustomUser


class ScopedManager(models.Manager):
    """
    Abstract base manager for user permission filtering in MCP agent contexts.

    This manager provides a reusable pattern for implementing user-based permission
    filtering across different models. It handles:
    - User validation and error handling
    - Superuser bypass (full access)
    - Secure defaults (empty queryset for invalid users)

    Security Model:
    - Invalid user ID: No access (returns empty queryset)
    - Superusers: Full access to all records
    - Regular users: Access determined by subclass implementation

    Usage:
        MyModel.scoped.for_user(user_id)  # Returns filtered queryset
    """

    def for_user(self, user) -> QuerySet:
        """
        Returns queryset filtered by user permissions.

        This method enforces permission filtering based on the provided user.
        Implements a secure-by-default approach:
        - Invalid user: empty queryset
        - Superuser: full access
        - Regular user: delegated to subclass for filtering

        Args:
            user: CustomUser instance

        Returns:
            QuerySet filtered by user permissions
        """
        from grit.auth.models import CustomUser

        try:
            # Superusers see all records
            if user.is_superuser:
                return super().get_queryset()
            # Regular users get filtered queryset
            return self.get_queryset().filter(owner=user)

        except CustomUser.DoesNotExist:
            # Invalid user ID - no access
            return super().get_queryset().none()
