from grit.core.core_base_settings import BaseSettings


class CoreSettings(BaseSettings):
    """Default core settings. Can be overridden in app.settings."""
    SETTINGS_KEY = 'CORE_SETTINGS'

    SUBDOMAIN_NAME: str = 'www'
    TIME_ZONE: str = 'UTC'

core_settings = CoreSettings()