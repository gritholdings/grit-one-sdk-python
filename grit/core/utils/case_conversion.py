import logging
import copy
import re
from typing import Any, Dict, List, Union
from django.urls import reverse, NoReverseMatch
from grit.core.types import AppMetadataSettingsTypedDict
logger = logging.getLogger(__name__)


def camel_to_snake(camel_str: str) -> str:
    snake_str = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', camel_str)
    snake_str = re.sub('([a-z0-9])([A-Z])', r'\1_\2', snake_str)
    return snake_str.lower()


def snake_to_camel(snake_str: str) -> str:
    components = snake_str.split('_')
    return components[0] + ''.join(x.title() for x in components[1:])


def convert_keys_to_camel_case(data: Union[Dict, List, Any]) -> Union[Dict, List, Any]:
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
    resolved_settings = copy.deepcopy(settings)
    apps_config = resolved_settings.get('APPS', {})
    models_config = resolved_settings.get('MODELS', {})
    tabs_config = resolved_settings.get('TABS', {})
    for app_key, app_config in apps_config.items():
        tabs = app_config.get('tabs', [])
        resolved_settings['APPS'][app_key]['tab_urls'] = {}
        for tab_key in tabs:
            if tab_key in models_config:
                app_prefixed_url = f'/app/{app_key}/m/{tab_key}/list'
                resolved_settings['APPS'][app_key]['tab_urls'][tab_key] = app_prefixed_url
                logger.debug(
                    f"Generated app-prefixed URL '{app_prefixed_url}' for model '{tab_key}' in app '{app_key}'"
                )
    if 'TABS' in resolved_settings and isinstance(resolved_settings['TABS'], dict):
        for tab_key, tab_config in resolved_settings['TABS'].items():
            if isinstance(tab_config, dict) and 'url_name' in tab_config:
                url_name = tab_config['url_name']
                try:
                    resolved_url = reverse(url_name)
                    tab_config['url'] = resolved_url
                    logger.debug(f"Resolved URL name '{url_name}' to '{resolved_url}' for tab '{tab_key}'")
                except NoReverseMatch as e:
                    logger.warning(
                        f"Failed to resolve URL name '{url_name}' for tab '{tab_key}': {e}. "
                        f"The frontend may not be able to navigate to this tab."
                    )
    return resolved_settings