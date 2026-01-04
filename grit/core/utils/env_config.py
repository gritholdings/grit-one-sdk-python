import os
import json
from pathlib import Path
import app.settings
from app.settings import DOMAIN_NAME
from grit.core.core_settings import core_settings

PLATFORM_NAME: str = getattr(app.settings, 'PLATFORM_NAME', 'platform')

# Cache for credentials loaded from file (None means not yet loaded)
_credentials_cache: dict | None = None


def get_django_env() -> str:
    """
    Set a default value of 'DEV' if the environment variable is not found
    """
    return os.getenv('DJANGO_ENV', 'DEV')

DJANGO_ENV = get_django_env()


def _get_credentials_file_path() -> Path:
    """Get the path to the credentials.json file relative to project root."""
    # Navigate from grit/core/utils/ up to project root
    return Path(__file__).resolve().parent.parent.parent.parent / 'credentials.json'


def _load_credentials_file() -> dict:
    """
    Load credentials from credentials.json file once and cache the result.
    Returns an empty dict if the file doesn't exist or is inaccessible.
    """
    global _credentials_cache

    if _credentials_cache is not None:
        return _credentials_cache

    credentials_path = _get_credentials_file_path()

    if credentials_path.exists():
        try:
            with open(credentials_path, encoding='utf-8') as f:
                _credentials_cache = json.load(f)
        except (IOError, json.JSONDecodeError):
            # File exists but couldn't be read or parsed
            _credentials_cache = {}
    else:
        # File doesn't exist, use empty dict (will fall back to env vars)
        _credentials_cache = {}

    return _credentials_cache


def load_credential(key_name: str, default: str = '') -> str:
    """
    Load a credential by key name.

    Priority:
    1. credentials.json file (if available)
    2. Environment variables
    3. Default value

    Args:
        key_name: The name of the credential to load
        default: Default value if credential is not found in any source

    Returns:
        The credential value or the default
    """
    credentials = _load_credentials_file()

    # Try credentials file first
    if key_name in credentials and credentials[key_name]:
        return credentials[key_name]

    # Fall back to environment variable
    return os.getenv(key_name, default)


def set_environ_credential(key_name: str) -> None:
    """Set an environment variable from a credential."""
    value = load_credential(key_name)
    if value:
        os.environ[key_name] = value

def get_base_url() -> str:
    """Get backend API base URL based on environment.
    For example:
    - Getting base_url for S3 file download.
    """
    base_url = ''
    if DJANGO_ENV != 'PROD':
        base_url = "http://127.0.0.1:8000"
    else:
        base_url = f"https://{core_settings.SUBDOMAIN_NAME}.{DOMAIN_NAME}"
    return base_url

def get_platform_url() -> str:
    """Get frontend platform URL based on environment.
    For example:
    - Getting platform URL for frontend access.
    """
    platform_url = ''
    if DJANGO_ENV != 'PROD':
        platform_url = "http://127.0.0.1:3000"
    else:
        platform_url = f"https://{PLATFORM_NAME}.{DOMAIN_NAME}"
    return platform_url