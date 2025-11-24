"""
Model Context Protocol (MCP) Server

This module provides an in-process MCP server that exposes registered Django models
as queryable tools for internal AI agents. It follows the same decorator pattern
as the metadata registration system.

Usage:
    from core_agent.mcp_server import mcp_registry, ModelQueryToolset
    from myapp.models import Account

    @mcp_registry.register(Account)
    class AccountQueryTool(ModelQueryToolset):
        model = Account

        def get_queryset(self):
            # Access self.request to filter the queryset
            return super().get_queryset().filter(location__isnull=False)

Security:
    - All operations are read-only regardless of user permissions
    - Requires Django session authentication
    - Respects APP_METADATA_SETTINGS permissions (groups and profiles)
    - Opt-in registration - models only exposed when explicitly registered
"""

from typing import Dict, List, Any, Optional
from django.db.models import Model, QuerySet
from django.http import HttpRequest, Http404
from django.core.exceptions import FieldDoesNotExist
from core.utils.case_conversion import camel_to_snake


class ModelQueryToolset:
    """
    Base class for MCP model query toolsets.

    Subclass this to expose a Django model for read-only querying by AI agents.
    Override get_queryset() to apply custom filtering based on the request user.

    Attributes:
        model: The Django model class to expose
        request: The current HTTP request (available in all methods)

    Example:
        @mcp_registry.register(Account)
        class AccountQueryTool(ModelQueryToolset):
            model = Account

            def get_queryset(self):
                # Filter based on user's permissions
                if self.request.user.is_superuser:
                    return super().get_queryset()
                return super().get_queryset().filter(owner=self.request.user)
    """

    model: Model = None
    request: HttpRequest = None

    # Maximum number of results to return (prevent excessive data transfer)
    max_results: int = 100

    def __init__(self, request: HttpRequest):
        """
        Initialize the toolset with the current request.

        Args:
            request: The HTTP request object containing user and session info
        """
        if self.model is None:
            raise ValueError(f"{self.__class__.__name__} must define a 'model' attribute")

        self.request = request

    def get_queryset(self) -> QuerySet:
        """
        Get the base queryset for this model.

        Override this method to apply custom filtering based on self.request.
        The default implementation returns all objects.

        Returns:
            QuerySet for the model

        Example:
            def get_queryset(self):
                # Only show records from user's account
                return super().get_queryset().filter(
                    account=self.request.user.account
                )
        """
        return self.model.objects.all()

    def list(self, filters: Optional[Dict[str, Any]] = None, limit: Optional[int] = None) -> Dict[str, Any]:
        """
        List model instances with optional filtering.

        Args:
            filters: Dictionary of field lookups (e.g., {'name__icontains': 'test'})
            limit: Maximum number of results (defaults to self.max_results)

        Returns:
            Dictionary with 'count' and 'results' keys
        """
        queryset = self.get_queryset()

        # Apply filters if provided
        if filters:
            # Validate filters to prevent injection attacks
            validated_filters = self._validate_filters(filters)
            queryset = queryset.filter(**validated_filters)

        # Apply limit
        if limit is None:
            limit = self.max_results
        else:
            # Enforce maximum limit
            limit = min(limit, self.max_results)

        # Get total count before limiting
        total_count = queryset.count()

        # Limit results
        results = queryset[:limit]

        # Serialize results
        serialized_results = [
            self._serialize_instance(instance)
            for instance in results
        ]

        return {
            'count': total_count,
            'limit': limit,
            'results': serialized_results
        }

    def retrieve(self, pk: str) -> Dict[str, Any]:
        """
        Retrieve a single model instance by primary key.

        Args:
            pk: Primary key of the instance

        Returns:
            Serialized instance data

        Raises:
            Http404: If instance not found or user lacks permission
        """
        try:
            instance = self.get_queryset().get(pk=pk)
            return self._serialize_instance(instance)
        except self.model.DoesNotExist:
            raise Http404(f"{self.model.__name__} with id {pk} not found")

    def search(self, query: str, search_fields: Optional[List[str]] = None, limit: Optional[int] = None) -> Dict[str, Any]:
        """
        Search across multiple fields using case-insensitive contains.

        Args:
            query: Search query string
            search_fields: List of field names to search (defaults to model's string fields)
            limit: Maximum number of results

        Returns:
            Dictionary with 'count' and 'results' keys
        """
        from django.db.models import Q

        queryset = self.get_queryset()

        if not search_fields:
            # Auto-detect text fields
            search_fields = self._get_searchable_fields()

        if not search_fields:
            # No searchable fields found
            return {'count': 0, 'limit': 0, 'results': []}

        # Build Q objects for OR search across fields
        q_objects = Q()
        for field_name in search_fields:
            q_objects |= Q(**{f"{field_name}__icontains": query})

        queryset = queryset.filter(q_objects)

        # Apply limit
        if limit is None:
            limit = self.max_results
        else:
            limit = min(limit, self.max_results)

        total_count = queryset.count()
        results = queryset[:limit]

        serialized_results = [
            self._serialize_instance(instance)
            for instance in results
        ]

        return {
            'count': total_count,
            'limit': limit,
            'results': serialized_results
        }

    def _validate_filters(self, filters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate filter parameters to prevent injection attacks.

        Only allows filtering on actual model fields with standard lookups.

        Args:
            filters: Dictionary of filter parameters

        Returns:
            Validated filters dictionary

        Raises:
            ValueError: If invalid field or lookup is used
        """
        validated = {}
        allowed_lookups = [
            'exact', 'iexact', 'contains', 'icontains',
            'in', 'gt', 'gte', 'lt', 'lte',
            'startswith', 'istartswith', 'endswith', 'iendswith',
            'range', 'isnull', 'regex', 'iregex'
        ]

        for key, value in filters.items():
            # Parse field name and lookup
            parts = key.split('__')
            field_name = parts[0]
            lookup = parts[1] if len(parts) > 1 else 'exact'

            # Validate field exists on model
            try:
                self.model._meta.get_field(field_name)
            except FieldDoesNotExist:
                raise ValueError(f"Invalid field: {field_name}")

            # Validate lookup is allowed
            if lookup not in allowed_lookups:
                raise ValueError(f"Invalid lookup: {lookup}")

            validated[key] = value

        return validated

    def _get_searchable_fields(self) -> List[str]:
        """
        Get list of text fields that can be searched.

        Returns:
            List of field names that are CharField or TextField
        """
        from django.db.models import CharField, TextField

        searchable = []
        for field in self.model._meta.get_fields():
            if isinstance(field, (CharField, TextField)):
                searchable.append(field.name)

        return searchable

    def _serialize_instance(self, instance: Model) -> Dict[str, Any]:
        """
        Serialize a model instance to a dictionary.

        Override this method to customize serialization.

        Args:
            instance: Model instance to serialize

        Returns:
            Dictionary representation of the instance
        """
        data = {
            'id': str(instance.pk),
        }

        # Add all field values
        for field in instance._meta.get_fields():
            # Skip reverse relations and many-to-many fields
            if field.is_relation and not field.concrete:
                continue

            # Skip many-to-many fields (they have a special manager)
            if field.many_to_many:
                continue

            field_name = field.name
            try:
                value = getattr(instance, field_name)

                # Convert to JSON-serializable format
                if value is None:
                    data[field_name] = None
                elif hasattr(value, 'isoformat'):
                    # DateTime objects
                    data[field_name] = value.isoformat()
                elif isinstance(value, Model):
                    # Foreign key - include id and string representation
                    data[field_name] = {
                        'id': str(value.pk),
                        'display': str(value)
                    }
                else:
                    data[field_name] = value
            except AttributeError:
                # Skip fields that can't be accessed
                continue

        return data


class MCPRegistry:
    """
    Registry for MCP model query toolsets.

    This follows the same pattern as the metadata registry system.
    Use the decorator pattern to register toolsets for models.

    The registry supports two registration modes:
    1. Auto-discovery: Models with 'scoped' managers are automatically registered
    2. Manual registration: Use @mcp_registry.register() decorator for custom toolsets

    Manual registrations override auto-discovered ones, allowing custom behavior.

    Example:
        @mcp_registry.register(Account)
        class AccountQueryTool(ModelQueryToolset):
            model = Account
    """

    def __init__(self):
        self._registry: Dict[Model, type] = {}
        self._auto_discovered: bool = False
        # Add ModelQueryToolset as an attribute for backward compatibility
        self.ModelQueryToolset = ModelQueryToolset

    def register(self, model_class: type):
        """
        Decorator to register a toolset for a model class.

        Args:
            model_class: The Django model class to register a toolset for

        Returns:
            Decorator function that registers the toolset class

        Example:
            @mcp_registry.register(Account)
            class AccountQueryTool(ModelQueryToolset):
                model = Account
        """
        def decorator(toolset_class):
            self._registry[model_class] = toolset_class
            return toolset_class
        return decorator

    def get(self, model_class: type) -> Optional[type]:
        """
        Get the toolset class for a model.

        Args:
            model_class: The Django model class

        Returns:
            The registered toolset class, or None if not registered
        """
        return self._registry.get(model_class)

    def get_by_name(self, model_name: str) -> Optional[type]:
        """
        Get the toolset class by model name (case-insensitive).

        Args:
            model_name: The model name (e.g., 'Account', 'account')

        Returns:
            The registered toolset class, or None if not registered
        """
        model_name_lower = model_name.lower()

        for model_class, toolset_class in self._registry.items():
            if model_class.__name__.lower() == model_name_lower:
                return toolset_class, model_class

        return None, None

    def get_registered_models(self) -> Dict[type, type]:
        """
        Get all registered models and their toolset classes.

        Returns:
            Dictionary mapping model classes to toolset classes
        """
        return dict(self._registry)

    def list_available_tools(self) -> List[Dict[str, str]]:
        """
        List all available tools (registered models).

        Returns:
            List of dictionaries with tool metadata
        """
        tools = []
        for model_class in self._registry.keys():
            model_name = model_class.__name__
            model_name_snake = camel_to_snake(model_name)

            tools.append({
                'name': model_name,
                'name_snake': model_name_snake,
                'description': f"Query {model_name} records",
                'operations': ['list', 'retrieve', 'search']
            })

        return tools

    def get_models_with_user_mode(self) -> List[type]:
        """
        Get all registered models that have a scoped manager.

        This is used by BaseOpenAIUserModeAgent to determine which models
        are accessible for querying through MCP tools.

        Returns:
            List of model classes that have a 'scoped' manager attribute
        """
        models_with_scoped = []

        for model_class in self._registry.keys():
            # Check if the model has a scoped attribute
            if hasattr(model_class, 'scoped'):
                scoped_attr = getattr(model_class, 'scoped')
                # Verify it's a manager (not just any attribute)
                from django.db.models import Manager
                if isinstance(scoped_attr, Manager):
                    models_with_scoped.append(model_class)

        return models_with_scoped

    def register_default(self, model_class: type) -> type:
        """
        Register a model with a default ModelQueryToolset.

        This creates a simple toolset class that uses the model's scoped manager
        for queryset filtering. The toolset will call scoped.for_user(user)
        to properly filter results based on user permissions.

        Args:
            model_class: The Django model class to register

        Returns:
            The created toolset class
        """
        # Create a dynamic toolset class for this model
        def get_user_filtered_queryset(self):
            """Get queryset filtered by current user via scoped manager."""
            scoped_manager = getattr(model_class, 'scoped')
            return scoped_manager.for_user(self.request.user)

        toolset_class = type(
            f"{model_class.__name__}DefaultQueryTool",
            (ModelQueryToolset,),
            {
                'model': model_class,
                'get_queryset': get_user_filtered_queryset
            }
        )

        # Register it
        self._registry[model_class] = toolset_class
        return toolset_class

    def auto_discover(self):
        """
        Auto-discover and register all Django models with scoped managers.

        This scans all installed Django apps for models that have a 'scoped'
        manager attribute. Models are registered with a default toolset unless
        they're already manually registered.

        Manual registrations always take precedence over auto-discovered ones.
        This allows models with complex permission logic to have custom toolsets
        while simple models can rely on auto-discovery.

        This method should be called once during Django's app initialization.
        """
        if self._auto_discovered:
            # Already discovered, don't run again
            return

        from django.apps import apps
        from django.db.models import Manager

        discovered_count = 0

        # Iterate through all installed models
        for model_class in apps.get_models():
            # Check if model has scoped manager
            if hasattr(model_class, 'scoped'):
                scoped_attr = getattr(model_class, 'scoped')

                # Verify it's actually a Manager instance
                if isinstance(scoped_attr, Manager):
                    # Only register if not already manually registered
                    if model_class not in self._registry:
                        self.register_default(model_class)
                        discovered_count += 1

        self._auto_discovered = True

        # Log discovery results (optional, can be removed if too verbose)
        if discovered_count > 0:
            import logging
            logger = logging.getLogger(__name__)
            logger.debug(f"MCP auto-discovery: registered {discovered_count} models with scoped managers")


# Create global registry instance
mcp_registry = MCPRegistry()

# Make ModelQueryToolset available as an attribute
mcp_registry.ModelQueryToolset = ModelQueryToolset

__all__ = ['ModelQueryToolset', 'mcp_registry']
