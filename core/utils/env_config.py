import os
import json
from app.settings import DOMAIN_NAME, SUBDOMAIN_NAME


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
    base_url = ''
    if DJANGO_ENV != 'PROD':
        base_url = "http://127.0.0.1:8000"
    else:
        base_url = f"https://{SUBDOMAIN_NAME}.{DOMAIN_NAME}"
    return base_url

def get_platform_url() -> str:
    platform_url = ''
    if DJANGO_ENV != 'PROD':
        platform_url = "http://127.0.0.1:3000"
    else:
        platform_url = f"https://platform.{DOMAIN_NAME}"
    return platform_url