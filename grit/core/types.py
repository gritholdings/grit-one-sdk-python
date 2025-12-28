from typing import TypedDict, List, Dict, Literal, Any
from typing_extensions import NotRequired


# Flexible type for app-level settings that override/extend core settings
AdditionalSettingsType = Dict[str, Any]


class CoreSettingsTypedDict(TypedDict):
    SUBDOMAIN_NAME: NotRequired[str]
    TIME_ZONE: NotRequired[str]


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


class VisibilityItemTypedDict(TypedDict):
    visible: bool


class TabVisibilityItemTypedDict(TypedDict):
    visibility: Literal['visible', 'hidden']


class VisibilityConfigTypedDict(TypedDict):
    app_visibilities: NotRequired[Dict[str, VisibilityItemTypedDict]]
    tab_visibilities: NotRequired[Dict[str, TabVisibilityItemTypedDict]]


class ModelPermissionsTypedDict(TypedDict):
    allow_create: NotRequired[bool]
    allow_read: NotRequired[bool]
    allow_edit: NotRequired[bool]
    allow_delete: NotRequired[bool]
    view_all_fields: NotRequired[bool]


class FieldPermissionsTypedDict(TypedDict):
    readable: NotRequired[bool]
    editable: NotRequired[bool]


class ChoiceItemTypedDict(TypedDict):
    label: str
    closure_type: str
    is_active: bool
    probability: NotRequired[int]


class ProfileConfigTypedDict(TypedDict):
    app_visibilities: NotRequired[Dict[str, VisibilityItemTypedDict]]
    tab_visibilities: NotRequired[Dict[str, TabVisibilityItemTypedDict]]
    model_permissions: NotRequired[Dict[str, ModelPermissionsTypedDict]]
    field_permissions: NotRequired[Dict[str, FieldPermissionsTypedDict]]


class AppMetadataSettingsTypedDict(TypedDict):
    APPS: NotRequired[Dict[str, AppConfigTypedDict]]
    MODELS: NotRequired[Dict[str, Dict[str, str]]]
    TABS: NotRequired[Dict[str, TabConfigTypedDict]]
    GROUPS: NotRequired[Dict[str, VisibilityConfigTypedDict]]
    PROFILES: NotRequired[Dict[str, ProfileConfigTypedDict]]
    CHOICES: NotRequired[Dict[str, Dict[str, ChoiceItemTypedDict]]]