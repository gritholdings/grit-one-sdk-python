import os
import json
import app.settings
from app.settings import DOMAIN_NAME
from core.core_settings import core_settings

PLATFORM_NAME: str = getattr(app.settings, 'PLATFORM_NAME', 'platform')


def get_django_env() -> str:
    """
    Set a default value of 'DEV' if the environment variable is not found
    """
    return os.getenv('DJANGO_ENV', 'DEV')

DJANGO_ENV = get_django_env()


def load_credential(key_name: str) -> str:
    with open(os.getcwd() + '/credentials.json') as f:
        credentials = json.load(f)
        return credentials[key_name]

def set_environ_credential(key_name: str) -> None:
    os.environ[key_name] = load_credential(key_name)
    return None

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