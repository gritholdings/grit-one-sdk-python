class ModelMetadata:
    """
    Base class for model metadata.
    This class can be extended to define specific metadata for models.
    """
    # List display fields for list views
    list_display = None
    
    # Fieldsets for organizing form fields
    fieldsets = None
    
    # Form class for editing
    form = None
    
    # Inline model configurations (list of inline classes)
    inlines = None
    
    def __init__(self):
        """Initialize metadata with default values."""
        if self.inlines is None:
            self.inlines = []


class MetadataRegistry:
    """Registry for model metadata classes."""
    
    def __init__(self):
        self._registry = {}
        # Add ModelMetadata as an attribute for backward compatibility
        self.ModelMetadata = ModelMetadata
    
    def register(self, model_class):
        """
        Decorator to register metadata for a model class.
        
        Args:
            model_class: The model class to register metadata for.
        
        Returns:
            A decorator function that registers the metadata class.
        """
        def decorator(metadata_class):
            self._registry[model_class] = metadata_class
            return metadata_class
        return decorator
    
    def get(self, model_class):
        """Get metadata for a model class."""
        return self._registry.get(model_class)
    
    def get_urlpatterns(self):
        """
        Generate URL patterns for all registered models.
        
        Returns:
            A list of URL patterns for registered models.
        """
        from django.urls import path
        from .views import MetadataViewGenerator
        
        patterns = []
        view_generator = MetadataViewGenerator()
        
        for model_class, metadata_class in self._registry.items():
            model_name = model_class.__name__
            model_name_lower = model_name.lower()
            
            # Generate list view URL
            list_view = view_generator.create_list_view(model_class, metadata_class)
            patterns.append(
                path(
                    f'm/{model_name}/list',
                    list_view,
                    name=f'{model_name_lower}_listview'
                )
            )
            
            # Generate detail view URL
            detail_view = view_generator.create_detail_view(model_class, metadata_class)
            patterns.append(
                path(
                    f'r/{model_name}/<uuid:{model_name_lower}_id>/view',
                    detail_view,
                    name=f'{model_name_lower}_detailview'
                )
            )
            
            # Generate update view URL
            update_view = view_generator.create_update_view(model_class, metadata_class)
            patterns.append(
                path(
                    f'r/{model_name}/<uuid:{model_name_lower}_id>/update',
                    update_view,
                    name=f'{model_name_lower}_update'
                )
            )
            
            # Generate inline update view URL
            inline_update_view = view_generator.create_inline_update_view(model_class, metadata_class)
            patterns.append(
                path(
                    f'r/{model_name}/<uuid:{model_name_lower}_id>/inline/<str:inline_model>/update',
                    inline_update_view,
                    name=f'{model_name_lower}_inline_update'
                )
            )
            
            # Generate available items view URL (for fetching available items for inline relationships)
            available_items_view = view_generator.create_available_items_view(model_class, metadata_class)
            patterns.append(
                path(
                    f'r/{model_name}/<uuid:{model_name_lower}_id>/available_<str:inline_type>/',
                    available_items_view,
                    name=f'{model_name_lower}_available_items'
                )
            )
            
            # Generate delete view URL
            delete_view = view_generator.create_delete_view(model_class, metadata_class)
            patterns.append(
                path(
                    f'r/{model_name}/<uuid:{model_name_lower}_id>/delete',
                    delete_view,
                    name=f'{model_name_lower}_delete'
                )
            )
        
        return patterns
    
    def get_registered_models(self):
        """
        Get all registered models and their metadata classes.
        
        Returns:
            A dictionary of model classes to metadata classes.
        """
        return dict(self._registry)


# Create a global registry instance
metadata = MetadataRegistry()

# Make ModelMetadata available as an attribute of metadata for imports
metadata.ModelMetadata = ModelMetadata

__all__ = ['ModelMetadata', 'metadata']