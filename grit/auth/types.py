from typing import TypedDict, Literal
from typing_extensions import NotRequired


class AuthSettingsTypedDict(TypedDict):
    LOGIN_VIEW: NotRequired[str]
    EMAIL_VERIFICATION: NotRequired[Literal['mandatory', 'optional', 'skip']]
    EMAIL_VERIFICATION_EXPIRY_HOURS: NotRequired[int]
    EMAIL_VERIFICATION_RESEND_COOLDOWN_SECONDS: NotRequired[int]
    SIGNUP_REDIRECT_URL: NotRequired[str]
    MFA_ENFORCEMENT: NotRequired[Literal['mandatory', 'optional', 'disabled']]
    MFA_METHODS: NotRequired[list[str]]
    MFA_BACKUP_CODE_COUNT: NotRequired[int]
    MFA_CODE_EXPIRY_SECONDS: NotRequired[int]