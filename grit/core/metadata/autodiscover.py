"""
Auto-discovery mechanism for model metadata registration.
Similar to Django's admin autodiscover functionality.
"""

import logging
from importlib import import_module
from django.apps import apps
from django.utils.module_loading import module_has_submodule

logger = logging.getLogger(__name__)


def autodiscover():
    """
    Automatically discover and import metadata.py modules from all installed apps.
    This function should be called during Django's startup process.
    """
    for app_config in apps.get_app_configs():
        # Skip Django's built-in apps
        if app_config.name.startswith('django.'):
            continue
            
        # Check if the app has a metadata module
        if module_has_submodule(app_config.module, 'metadata'):
            try:
                # Import the metadata module to trigger registrations
                import_module(f'{app_config.name}.metadata')
                logger.debug(f"Successfully imported metadata from {app_config.name}")
            except ImportError as e:
                logger.warning(f"Failed to import metadata from {app_config.name}: {e}")
            except Exception as e:
                logger.error(f"Error loading metadata from {app_config.name}: {e}")