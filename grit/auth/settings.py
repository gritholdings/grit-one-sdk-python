from typing import Literal
from grit.core.core_base_settings import BaseSettings


class AuthSettings(BaseSettings):
    SETTINGS_KEY = 'AUTH_SETTINGS'
    LOGIN_VIEW: str = 'grit.auth.views.custom_login_view'
    EMAIL_VERIFICATION: Literal['mandatory', 'optional', 'skip'] = 'optional'
    EMAIL_VERIFICATION_EXPIRY_HOURS: int = 48
    EMAIL_VERIFICATION_RESEND_COOLDOWN_SECONDS: int = 60
    SIGNUP_REDIRECT_URL: str = 'index'
auth_settings: AuthSettings = AuthSettings()