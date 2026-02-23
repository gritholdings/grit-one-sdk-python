class ModelMetadata:
    list_display = None
    list_actions = None
    list_bulk_actions = None
    detail_actions = None
    fieldsets = None
    form = None
    inlines = None
    ordering = None
    def __init__(self):
        if self.inlines is None:
            self.inlines = []


class MetadataRegistry:
    def __init__(self):
        self._registry = {}
        self.ModelMetadata = ModelMetadata
    def register(self, model_class):
        def decorator(metadata_class):
            self._registry[model_class] = metadata_class
            return metadata_class
        return decorator
    def get(self, model_class):
        return self._registry.get(model_class)
    def _get_app_for_model(self, model_class):
        from grit.core.utils.case_conversion import camel_to_snake
        from app.settings import APP_METADATA_SETTINGS
        model_name_snake = camel_to_snake(model_class.__name__)
        apps_config = APP_METADATA_SETTINGS.get('APPS', {})
        for app_key, app_config in apps_config.items():
            tabs = app_config.get('tabs', [])
            if model_name_snake in tabs:
                return app_key
        app_label = model_class._meta.app_label
        if app_label.startswith('core_'):
            return app_label[5:]
        return app_label
    def _get_all_apps_for_model(self, model_class):
        from grit.core.utils.case_conversion import camel_to_snake
        from app.settings import APP_METADATA_SETTINGS
        model_name_snake = camel_to_snake(model_class.__name__)
        apps_config = APP_METADATA_SETTINGS.get('APPS', {})
        matching_apps = []
        for app_key, app_config in apps_config.items():
            tabs = app_config.get('tabs', [])
            if model_name_snake in tabs:
                matching_apps.append(app_key)
        if not matching_apps:
            app_label = model_class._meta.app_label
            if app_label.startswith('core_'):
                matching_apps.append(app_label[5:])
            else:
                matching_apps.append(app_label)
        return matching_apps
    def get_urlpatterns(self):
        from django.urls import path
        from .views import MetadataViewGenerator
        from grit.core.utils.case_conversion import camel_to_snake
        patterns = []
        view_generator = MetadataViewGenerator()
        for model_class, metadata_class in self._registry.items():
            model_name = model_class.__name__
            model_name_lower = camel_to_snake(model_name)
            app_names = self._get_all_apps_for_model(model_class)
            primary_app = app_names[0]
            list_view = view_generator.create_list_view(model_class, metadata_class)
            detail_view = view_generator.create_detail_view(model_class, metadata_class)
            create_view = view_generator.create_create_view(model_class, metadata_class)
            update_view = view_generator.create_update_view(model_class, metadata_class)
            inline_update_view = view_generator.create_inline_update_view(model_class, metadata_class)
            available_items_view = view_generator.create_available_items_view(model_class, metadata_class)
            delete_view = view_generator.create_delete_view(model_class, metadata_class)
            bulk_action_view = view_generator.create_bulk_action_view(model_class, metadata_class)
            for i, app_name in enumerate(app_names):
                url_suffix = '' if i == 0 else f'_{app_name}'
                patterns.append(
                    path(
                        f'app/{app_name}/m/{model_name_lower}/list',
                        list_view,
                        name=f'{model_name_lower}_listview{url_suffix}'
                    )
                )
                patterns.append(
                    path(
                        f'app/{app_name}/r/{model_name_lower}/<uuid:{model_name_lower}_id>/view',
                        detail_view,
                        name=f'{model_name_lower}_detailview{url_suffix}'
                    )
                )
                patterns.append(
                    path(
                        f'app/{app_name}/m/{model_name_lower}/create',
                        create_view,
                        name=f'{model_name_lower}_create{url_suffix}'
                    )
                )
                patterns.append(
                    path(
                        f'app/{app_name}/r/{model_name_lower}/<uuid:{model_name_lower}_id>/update',
                        update_view,
                        name=f'{model_name_lower}_update{url_suffix}'
                    )
                )
                patterns.append(
                    path(
                        f'app/{app_name}/r/{model_name_lower}/<uuid:{model_name_lower}_id>/inline/<str:inline_model>/update',
                        inline_update_view,
                        name=f'{model_name_lower}_inline_update{url_suffix}'
                    )
                )
                patterns.append(
                    path(
                        f'app/{app_name}/r/{model_name_lower}/<uuid:{model_name_lower}_id>/available_<str:inline_type>/',
                        available_items_view,
                        name=f'{model_name_lower}_available_items{url_suffix}'
                    )
                )
                patterns.append(
                    path(
                        f'app/{app_name}/r/{model_name_lower}/<uuid:{model_name_lower}_id>/delete',
                        delete_view,
                        name=f'{model_name_lower}_delete{url_suffix}'
                    )
                )
                patterns.append(
                    path(
                        f'app/{app_name}/m/{model_name_lower}/bulk-action',
                        bulk_action_view,
                        name=f'{model_name_lower}_bulk_action{url_suffix}'
                    )
                )
            from .views import LegacyRedirectView
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
        return dict(self._registry)
metadata = MetadataRegistry()
metadata.ModelMetadata = ModelMetadata
__all__ = ['ModelMetadata', 'metadata']