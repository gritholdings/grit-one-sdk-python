from core.core_base_settings import BaseSettings


class AuthSettings(BaseSettings):
    """Default authentication settings. Can be overridden in app.settings."""
    SETTINGS_KEY = 'AUTH_SETTINGS'

    LOGIN_VIEW: str = 'customauth.views.custom_login_view'


auth_settings: AuthSettings = AuthSettings()