import logging
from importlib import import_module
from django.apps import apps
from django.utils.module_loading import module_has_submodule
logger = logging.getLogger(__name__)


def autodiscover():
    for app_config in apps.get_app_configs():
        if app_config.name.startswith('django.'):
            continue
        if module_has_submodule(app_config.module, 'metadata'):
            try:
                import_module(f'{app_config.name}.metadata')
                logger.debug(f"Successfully imported metadata from {app_config.name}")
            except ImportError as e:
                logger.warning(f"Failed to import metadata from {app_config.name}: {e}")
            except Exception as e:
                logger.error(f"Error loading metadata from {app_config.name}: {e}")