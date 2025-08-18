from core.core_base_settings import BaseSettings
from typing import TypedDict
from typing_extensions import NotRequired


class CoreSettingsTypedDict(TypedDict):
    pass

class CoreSettings(BaseSettings):
    """Default core settings. Can be overridden in app.settings."""
    SETTINGS_KEY = 'CORE_SETTINGS'

core_settings = CoreSettings()