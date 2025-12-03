from typing import Literal
from core.core_base_settings import BaseSettings


class AuthSettings(BaseSettings):
    """Default authentication settings. Can be overridden in app.settings."""
    SETTINGS_KEY = 'AUTH_SETTINGS'

    LOGIN_VIEW: str = 'customauth.views.custom_login_view'
    EMAIL_VERIFICATION: Literal['mandatory', 'optional', 'skip'] = 'optional'
    EMAIL_VERIFICATION_EXPIRY_HOURS: int = 48
    EMAIL_VERIFICATION_RESEND_COOLDOWN_SECONDS: int = 60  # Cooldown period in seconds
    SIGNUP_REDIRECT_URL: str = 'index'  # URL name to redirect after signup


auth_settings: AuthSettings = AuthSettings()