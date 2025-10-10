from typing import TypedDict, List, Dict, Literal
from typing_extensions import NotRequired


class CoreSettingsTypedDict(TypedDict):
    SUBDOMAIN_NAME: NotRequired[str]


class TabTypedDict(TypedDict):
    title: str
    url: str
    icon: str


class AppConfigTypedDict(TypedDict):
    label: str
    icon: str
    tabs: List[str]


class TabConfigTypedDict(TypedDict):
    label: str
    url_name: str
    icon: str


class VisibilityConfigTypedDict(TypedDict):
    app_visibility: NotRequired[Dict[str, Literal['visible', 'hidden']]]
    tab_visibility: NotRequired[Dict[str, Literal['visible', 'hidden']]]


class ProfileConfigTypedDict(TypedDict):
    allow_create: NotRequired[bool]
    allow_read: NotRequired[bool]
    allow_edit: NotRequired[bool]
    allow_delete: NotRequired[bool]


class AppMetadataSettingsTypedDict(TypedDict):
    APPS: Dict[str, AppConfigTypedDict]
    MODELS: Dict[str, Dict[str, str]]
    TABS: Dict[str, TabConfigTypedDict]
    GROUPS: Dict[str, VisibilityConfigTypedDict]
    PROFILES: Dict[str, Dict[str, ProfileConfigTypedDict]]