from typing import TypedDict
from typing_extensions import NotRequired


class AuthSettingsTypedDict(TypedDict):
    LOGIN_VIEW: NotRequired[str]