class ModelMetadata:
    """
    Base class for model metadata.
    This class can be extended to define specific metadata for models.
    """
    # List display fields for list views
    list_display = None

    # Actions available in list views
    list_actions = None
    
    # Actions available in detail views (component-based)
    detail_actions = None
    
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

    def _get_app_for_model(self, model_class):
        """
        Determine which app a model belongs to.

        Strategy:
        1. Check APP_METADATA_SETTINGS to find which app's tabs list contains this model
        2. Fall back to the model's app_label (strip 'core_' prefix if present)

        Args:
            model_class: The Django model class

        Returns:
            The app name (e.g., 'classroom', 'cms', 'sales')
        """
        from core.utils.case_conversion import camel_to_snake
        # Import directly from app.settings instead of django.conf.settings
        from app.settings import APP_METADATA_SETTINGS

        model_name_snake = camel_to_snake(model_class.__name__)

        # Get APPS config
        apps_config = APP_METADATA_SETTINGS.get('APPS', {})

        # Search through apps to find which one lists this model in its tabs
        for app_key, app_config in apps_config.items():
            tabs = app_config.get('tabs', [])
            if model_name_snake in tabs:
                return app_key

        # Fallback: use the model's app_label and strip 'core_' prefix
        app_label = model_class._meta.app_label
        if app_label.startswith('core_'):
            return app_label[5:]  # Remove 'core_' prefix
        return app_label
    
    def _get_all_apps_for_model(self, model_class):
        """
        Get ALL apps that include this model in their tabs.

        Unlike _get_app_for_model which returns the first match,
        this returns all apps so we can generate URLs for each.

        Args:
            model_class: The Django model class

        Returns:
            List of app names (e.g., ['classroom', 'agent_studio'])
        """
        from core.utils.case_conversion import camel_to_snake
        from app.settings import APP_METADATA_SETTINGS

        model_name_snake = camel_to_snake(model_class.__name__)
        apps_config = APP_METADATA_SETTINGS.get('APPS', {})

        matching_apps = []
        for app_key, app_config in apps_config.items():
            tabs = app_config.get('tabs', [])
            if model_name_snake in tabs:
                matching_apps.append(app_key)

        # If no apps found, use fallback
        if not matching_apps:
            app_label = model_class._meta.app_label
            if app_label.startswith('core_'):
                matching_apps.append(app_label[5:])
            else:
                matching_apps.append(app_label)

        return matching_apps

    def get_urlpatterns(self):
        """
        Generate URL patterns for all registered models.

        For models that appear in multiple apps' tabs, this generates
        URLs for each app (e.g., both /app/classroom/m/Agent/list
        and /app/agent_studio/m/Agent/list).

        Returns:
            A list of URL patterns for registered models, including both
            new app-prefixed URLs and legacy redirect URLs.
        """
        from django.urls import path
        from .views import MetadataViewGenerator
        from core.utils.case_conversion import camel_to_snake

        patterns = []
        view_generator = MetadataViewGenerator()

        for model_class, metadata_class in self._registry.items():
            model_name = model_class.__name__
            model_name_lower = camel_to_snake(model_name)

            # Get ALL apps this model belongs to
            app_names = self._get_all_apps_for_model(model_class)
            primary_app = app_names[0]  # First app for legacy redirects

            # Generate views (shared across all app contexts)
            list_view = view_generator.create_list_view(model_class, metadata_class)
            detail_view = view_generator.create_detail_view(model_class, metadata_class)
            create_view = view_generator.create_create_view(model_class, metadata_class)
            update_view = view_generator.create_update_view(model_class, metadata_class)
            inline_update_view = view_generator.create_inline_update_view(model_class, metadata_class)
            available_items_view = view_generator.create_available_items_view(model_class, metadata_class)
            delete_view = view_generator.create_delete_view(model_class, metadata_class)

            # ============================================================
            # NEW APP-PREFIXED URLs (Generate for EACH app)
            # ============================================================
            for i, app_name in enumerate(app_names):
                # For the primary app (first one), use standard URL names
                # For additional apps, add app suffix to avoid name conflicts
                url_suffix = '' if i == 0 else f'_{app_name}'

                # List view
                patterns.append(
                    path(
                        f'app/{app_name}/m/{model_name_lower}/list',
                        list_view,
                        name=f'{model_name_lower}_listview{url_suffix}'
                    )
                )

                # Detail view
                patterns.append(
                    path(
                        f'app/{app_name}/r/{model_name_lower}/<uuid:{model_name_lower}_id>/view',
                        detail_view,
                        name=f'{model_name_lower}_detailview{url_suffix}'
                    )
                )

                # Create view
                patterns.append(
                    path(
                        f'app/{app_name}/m/{model_name_lower}/create',
                        create_view,
                        name=f'{model_name_lower}_create{url_suffix}'
                    )
                )

                # Update view
                patterns.append(
                    path(
                        f'app/{app_name}/r/{model_name_lower}/<uuid:{model_name_lower}_id>/update',
                        update_view,
                        name=f'{model_name_lower}_update{url_suffix}'
                    )
                )

                # Inline update view
                patterns.append(
                    path(
                        f'app/{app_name}/r/{model_name_lower}/<uuid:{model_name_lower}_id>/inline/<str:inline_model>/update',
                        inline_update_view,
                        name=f'{model_name_lower}_inline_update{url_suffix}'
                    )
                )

                # Available items view
                patterns.append(
                    path(
                        f'app/{app_name}/r/{model_name_lower}/<uuid:{model_name_lower}_id>/available_<str:inline_type>/',
                        available_items_view,
                        name=f'{model_name_lower}_available_items{url_suffix}'
                    )
                )

                # Delete view
                patterns.append(
                    path(
                        f'app/{app_name}/r/{model_name_lower}/<uuid:{model_name_lower}_id>/delete',
                        delete_view,
                        name=f'{model_name_lower}_delete{url_suffix}'
                    )
                )

            # ============================================================
            # LEGACY REDIRECT URLs (Backwards compatibility)
            # Redirect to the primary app (first one in the list)
            # ============================================================
            from .views import LegacyRedirectView

            # List view redirect
            patterns.append(
                path(
                    f'm/{model_name_lower}/list',
                    LegacyRedirectView.as_view(
                        app_name=primary_app,
                        model_name=model_name_lower,
                        pattern_type='list'
                    ),
                    name=f'{model_name_lower}_listview_legacy'
                )
            )

            # Detail view redirect
            patterns.append(
                path(
                    f'r/{model_name_lower}/<uuid:{model_name_lower}_id>/view',
                    LegacyRedirectView.as_view(
                        app_name=primary_app,
                        model_name=model_name_lower,
                        pattern_type='detail'
                    ),
                    name=f'{model_name_lower}_detailview_legacy'
                )
            )

            # Create view redirect
            patterns.append(
                path(
                    f'm/{model_name_lower}/create',
                    LegacyRedirectView.as_view(
                        app_name=primary_app,
                        model_name=model_name_lower,
                        pattern_type='create'
                    ),
                    name=f'{model_name_lower}_create_legacy'
                )
            )

            # Update view redirect
            patterns.append(
                path(
                    f'r/{model_name_lower}/<uuid:{model_name_lower}_id>/update',
                    LegacyRedirectView.as_view(
                        app_name=primary_app,
                        model_name=model_name_lower,
                        pattern_type='update'
                    ),
                    name=f'{model_name_lower}_update_legacy'
                )
            )

            # Inline update view redirect
            patterns.append(
                path(
                    f'r/{model_name_lower}/<uuid:{model_name_lower}_id>/inline/<str:inline_model>/update',
                    LegacyRedirectView.as_view(
                        app_name=primary_app,
                        model_name=model_name_lower,
                        pattern_type='inline_update'
                    ),
                    name=f'{model_name_lower}_inline_update_legacy'
                )
            )

            # Available items view redirect
            patterns.append(
                path(
                    f'r/{model_name_lower}/<uuid:{model_name_lower}_id>/available_<str:inline_type>/',
                    LegacyRedirectView.as_view(
                        app_name=primary_app,
                        model_name=model_name_lower,
                        pattern_type='available_items'
                    ),
                    name=f'{model_name_lower}_available_items_legacy'
                )
            )

            # Delete view redirect
            patterns.append(
                path(
                    f'r/{model_name_lower}/<uuid:{model_name_lower}_id>/delete',
                    LegacyRedirectView.as_view(
                        app_name=primary_app,
                        model_name=model_name_lower,
                        pattern_type='delete'
                    ),
                    name=f'{model_name_lower}_delete_legacy'
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