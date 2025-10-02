from typing import TypedDict, Literal
from typing_extensions import NotRequired


class AuthSettingsTypedDict(TypedDict):
    LOGIN_VIEW: NotRequired[str]
    EMAIL_VERIFICATION: NotRequired[Literal['mandatory', 'optional', 'skip']]
    EMAIL_VERIFICATION_EXPIRY_HOURS: NotRequired[int]
    EMAIL_VERIFICATION_RESEND_COOLDOWN_SECONDS: NotRequired[int]