from typing import TypedDict, List
from typing_extensions import NotRequired


class NavItemTypedDict(TypedDict):
    title: str
    url: str
    icon: str


class AppConfigTypedDict(TypedDict):
    name: str
    logo: str
    url: str
    nav_items: List[NavItemTypedDict]  # Using snake_case for Python convention


class AppMetadataSettingsTypedDict(TypedDict):
    APPS: List[AppConfigTypedDict]