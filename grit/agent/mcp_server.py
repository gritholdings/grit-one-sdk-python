from typing import Dict, List, Any, Optional
from django.db.models import Model, QuerySet
from django.http import HttpRequest, Http404
from django.core.exceptions import FieldDoesNotExist
from grit.core.utils.case_conversion import camel_to_snake


class ModelQueryToolset:
    model: Model = None
    request: HttpRequest = None
    max_results: int = 100
    def __init__(self, request: HttpRequest):
        if self.model is None:
            raise ValueError(f"{self.__class__.__name__} must define a 'model' attribute")
        self.request = request
    def get_queryset(self) -> QuerySet:
        return self.model.objects.all()
    def list(self, filters: Optional[Dict[str, Any]] = None, limit: Optional[int] = None) -> Dict[str, Any]:
        queryset = self.get_queryset()
        if filters:
            validated_filters = self._validate_filters(filters)
            queryset = queryset.filter(**validated_filters)
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
    def retrieve(self, pk: str) -> Dict[str, Any]:
        try:
            instance = self.get_queryset().get(pk=pk)
            return self._serialize_instance(instance)
        except self.model.DoesNotExist:
            raise Http404(f"{self.model.__name__} with id {pk} not found")
    def search(self, query: str, search_fields: Optional[List[str]] = None, limit: Optional[int] = None) -> Dict[str, Any]:
        from django.db.models import Q
        queryset = self.get_queryset()
        if not search_fields:
            search_fields = self._get_searchable_fields()
        if not search_fields:
            return {'count': 0, 'limit': 0, 'results': []}
        q_objects = Q()
        for field_name in search_fields:
            q_objects |= Q(**{f"{field_name}__icontains": query})
        queryset = queryset.filter(q_objects)
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
        validated = {}
        allowed_lookups = [
            'exact', 'iexact', 'contains', 'icontains',
            'in', 'gt', 'gte', 'lt', 'lte',
            'startswith', 'istartswith', 'endswith', 'iendswith',
            'range', 'isnull', 'regex', 'iregex'
        ]
        for key, value in filters.items():
            parts = key.split('__')
            field_name = parts[0]
            lookup = parts[1] if len(parts) > 1 else 'exact'
            try:
                self.model._meta.get_field(field_name)
            except FieldDoesNotExist:
                raise ValueError(f"Invalid field: {field_name}")
            if lookup not in allowed_lookups:
                raise ValueError(f"Invalid lookup: {lookup}")
            validated[key] = value
        return validated
    def _get_searchable_fields(self) -> List[str]:
        from django.db.models import CharField, TextField
        searchable = []
        for field in self.model._meta.get_fields():
            if isinstance(field, (CharField, TextField)):
                searchable.append(field.name)
        return searchable
    def _serialize_instance(self, instance: Model) -> Dict[str, Any]:
        data = {
            'id': str(instance.pk),
        }
        for field in instance._meta.get_fields():
            if field.is_relation and not field.concrete:
                continue
            if field.many_to_many:
                continue
            field_name = field.name
            try:
                value = getattr(instance, field_name)
                if value is None:
                    data[field_name] = None
                elif hasattr(value, 'isoformat'):
                    data[field_name] = value.isoformat()
                elif isinstance(value, Model):
                    data[field_name] = {
                        'id': str(value.pk),
                        'display': str(value)
                    }
                else:
                    data[field_name] = value
            except AttributeError:
                continue
        return data


class MCPRegistry:
    def __init__(self):
        self._registry: Dict[Model, type] = {}
        self._auto_discovered: bool = False
        self.ModelQueryToolset = ModelQueryToolset
    def register(self, model_class: type):
        def decorator(toolset_class):
            self._registry[model_class] = toolset_class
            return toolset_class
        return decorator
    def get(self, model_class: type) -> Optional[type]:
        return self._registry.get(model_class)
    def get_by_name(self, model_name: str) -> Optional[type]:
        model_name_lower = model_name.lower()
        for model_class, toolset_class in self._registry.items():
            if model_class.__name__.lower() == model_name_lower:
                return toolset_class, model_class
        return None, None
    def get_registered_models(self) -> Dict[type, type]:
        return dict(self._registry)
    def list_available_tools(self) -> List[Dict[str, str]]:
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
        models_with_scoped = []
        for model_class in self._registry.keys():
            if hasattr(model_class, 'scoped'):
                scoped_attr = getattr(model_class, 'scoped')
                from django.db.models import Manager
                if isinstance(scoped_attr, Manager):
                    models_with_scoped.append(model_class)
        return models_with_scoped
    def register_default(self, model_class: type) -> type:
        def get_user_filtered_queryset(self):
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
        self._registry[model_class] = toolset_class
        return toolset_class
    def auto_discover(self):
        if self._auto_discovered:
            return
        from django.apps import apps
        from django.db.models import Manager
        discovered_count = 0
        for model_class in apps.get_models():
            if hasattr(model_class, 'scoped'):
                scoped_attr = getattr(model_class, 'scoped')
                if isinstance(scoped_attr, Manager):
                    if model_class not in self._registry:
                        self.register_default(model_class)
                        discovered_count += 1
        self._auto_discovered = True
        if discovered_count > 0:
            import logging
            logger = logging.getLogger(__name__)
            logger.debug(f"MCP auto-discovery: registered {discovered_count} models with scoped managers")
mcp_registry = MCPRegistry()
mcp_registry.ModelQueryToolset = ModelQueryToolset
__all__ = ['ModelQueryToolset', 'mcp_registry']
