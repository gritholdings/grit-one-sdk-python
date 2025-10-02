from core.core_base_settings import BaseSettings
from typing import TypedDict


class CoreSettings(BaseSettings):
    """Default core settings. Can be overridden in app.settings."""
    SETTINGS_KEY = 'CORE_SETTINGS'
    
    SUBDOMAIN_NAME: str = 'www'

core_settings = CoreSettings()