import os
import json
from pathlib import Path
from grit.core.core_settings import core_settings
DOMAIN_NAME: str = core_settings.DOMAIN_NAME
PLATFORM_NAME: str = core_settings.PLATFORM_NAME
_credentials_cache: dict | None = None
_secrets_manager_cache: dict | None = None


def get_django_env() -> str:
    return os.getenv('DJANGO_ENV', 'DEV')
DJANGO_ENV = get_django_env()


def _get_credentials_file_path() -> Path:
    return Path(__file__).resolve().parent.parent.parent.parent / 'credentials.json'


def _load_credentials_file() -> dict:
    global _credentials_cache
    if _credentials_cache is not None:
        return _credentials_cache
    credentials_path = _get_credentials_file_path()
    if credentials_path.exists():
        try:
            with open(credentials_path, encoding='utf-8') as f:
                _credentials_cache = json.load(f)
        except (IOError, json.JSONDecodeError):
            _credentials_cache = {}
    else:
        _credentials_cache = {}
    return _credentials_cache or {}


def _fetch_secrets_manager() -> dict:
    if get_django_env() != 'PROD':
        return {}
    secret_id = core_settings.AWS_SECRETS_MANAGER_SECRET_ID
    if not secret_id:
        return {}
    try:
        import boto3
        client = boto3.client('secretsmanager', region_name=core_settings.AWS_REGION)
        response = client.get_secret_value(SecretId=secret_id)
        parsed = json.loads(response.get('SecretString') or '{}')
        return parsed if isinstance(parsed, dict) else {}
    except Exception:
        return {}


def _load_secrets_manager() -> dict:
    global _secrets_manager_cache
    if _secrets_manager_cache is None:
        _secrets_manager_cache = _fetch_secrets_manager()
    return _secrets_manager_cache


def load_credential(key_name: str, default: str = '') -> str:
    credentials = _load_credentials_file()
    if key_name in credentials and credentials[key_name]:
        return credentials[key_name]
    secrets = _load_secrets_manager()
    if secrets.get(key_name):
        return secrets[key_name]
    return os.getenv(key_name, default)


def set_environ_credential(key_name: str) -> None:
    value = load_credential(key_name)
    if value:
        os.environ[key_name] = value


def get_base_url() -> str:
    base_url = ''
    if DJANGO_ENV != 'PROD':
        base_url = "http://127.0.0.1:8000"
    else:
        base_url = f"https://{core_settings.SUBDOMAIN_NAME}.{DOMAIN_NAME}"
    return base_url


def get_platform_url() -> str:
    platform_url = ''
    if DJANGO_ENV != 'PROD':
        platform_url = "http://127.0.0.1:3000"
    else:
        platform_url = f"https://{PLATFORM_NAME}.{DOMAIN_NAME}"
    return platform_url