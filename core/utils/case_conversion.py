"""
Utility functions for converting between snake_case and camelCase.
Used for serializing Python data structures to JavaScript-friendly format.
"""
import logging
import copy
import re
from typing import Any, Dict, List, Union
from django.urls import reverse, NoReverseMatch
from core.types import AppMetadataSettingsTypedDict

logger = logging.getLogger(__name__)


def camel_to_snake(camel_str: str) -> str:
    """
    Convert CamelCase or camelCase string to snake_case.

    Examples:
        CourseWork -> course_work
        NavItems -> nav_items
        appMetadataSettings -> app_metadata_settings
    """
    # Insert underscore before uppercase letters (except at the start)
    snake_str = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', camel_str)
    # Handle sequences of uppercase letters (e.g., HTTPResponse -> http_response)
    snake_str = re.sub('([a-z0-9])([A-Z])', r'\1_\2', snake_str)
    return snake_str.lower()


def snake_to_camel(snake_str: str) -> str:
    """
    Convert snake_case string to camelCase.
    
    Examples:
        nav_items -> navItems
        app_metadata_settings -> appMetadataSettings
    """
    components = snake_str.split('_')
    return components[0] + ''.join(x.title() for x in components[1:])


def convert_keys_to_camel_case(data: Union[Dict, List, Any]) -> Union[Dict, List, Any]:
    """
    Recursively convert all dictionary keys from snake_case to camelCase.

    This is used when serializing Python data structures for JavaScript/React frontend
    consumption, allowing Python code to follow PEP 8 conventions while providing
    camelCase JSON to the frontend.
    """
    if isinstance(data, dict):
        return {
            snake_to_camel(key) if isinstance(key, str) else key: convert_keys_to_camel_case(value)
            for key, value in data.items()
        }
    elif isinstance(data, list):
        return [convert_keys_to_camel_case(item) for item in data]
    else:
        return data


def resolve_urls_in_app_metadata(settings: AppMetadataSettingsTypedDict) -> Dict[str, Any]:
    """
    Resolve URL names to actual URL paths in APP_METADATA_SETTINGS.

    This function processes the TABS and APPS sections of APP_METADATA_SETTINGS:
    - For TABS with 'url_name': converts to 'url' using reverse()
    - For APPS with model-based tabs: generates app-prefixed URLs (/app/{app_name}/m/{Model}/list)

    Example:
        Input:  {'url_name': 'showcases_monte_carlo'}
        Output: {'url': '/showcases/monte-carlo/'}

        Input:  app 'classroom' with tab 'course'
        Output: {'url': '/app/classroom/m/Course/list'}

    Args:
        settings: The APP_METADATA_SETTINGS dictionary

    Returns:
        A deep copy of settings with resolved URL paths
    """
    # Deep copy to avoid modifying the original settings
    resolved_settings = copy.deepcopy(settings)

    # Get references to APPS, MODELS, and TABS
    apps_config = resolved_settings.get('APPS', {})
    models_config = resolved_settings.get('MODELS', {})
    tabs_config = resolved_settings.get('TABS', {})

    # Process each app and its tabs
    for app_key, app_config in apps_config.items():
        tabs = app_config.get('tabs', [])

        # Initialize tab_urls dict for this app to store app-specific URLs
        resolved_settings['APPS'][app_key]['tab_urls'] = {}

        for tab_key in tabs:
            # Check if this tab is a model (exists in MODELS config)
            if tab_key in models_config:
                # This is a model-based tab - generate app-prefixed URL
                # tab_key is already in snake_case, use it directly
                app_prefixed_url = f'/app/{app_key}/m/{tab_key}/list'

                # Store the URL in the app's tab_urls dict (not globally in MODELS)
                # This ensures each app has its own URL for shared models
                resolved_settings['APPS'][app_key]['tab_urls'][tab_key] = app_prefixed_url

                logger.debug(
                    f"Generated app-prefixed URL '{app_prefixed_url}' for model '{tab_key}' in app '{app_key}'"
                )

    # Process TABS section for custom (non-model) tabs
    if 'TABS' in resolved_settings and isinstance(resolved_settings['TABS'], dict):
        for tab_key, tab_config in resolved_settings['TABS'].items():
            if isinstance(tab_config, dict) and 'url_name' in tab_config:
                url_name = tab_config['url_name']
                try:
                    # Resolve the URL name to actual path
                    resolved_url = reverse(url_name)
                    # Add the resolved URL as 'url' field
                    tab_config['url'] = resolved_url
                    logger.debug(f"Resolved URL name '{url_name}' to '{resolved_url}' for tab '{tab_key}'")
                except NoReverseMatch as e:
                    # Log the error but keep the url_name for debugging
                    logger.warning(
                        f"Failed to resolve URL name '{url_name}' for tab '{tab_key}': {e}. "
                        f"The frontend may not be able to navigate to this tab."
                    )
                    # Optionally, set a fallback URL or leave url_name for frontend to handle
                    # For now, we'll just log and continue without adding 'url' field

    return resolved_settings