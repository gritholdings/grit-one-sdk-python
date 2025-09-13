"""
Utility functions for converting between snake_case and camelCase.
Used for serializing Python data structures to JavaScript-friendly format.
"""
import re
from typing import Any, Dict, List, Union


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