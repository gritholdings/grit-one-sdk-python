from typing import TypedDict, List, Optional
from typing_extensions import NotRequired


class AgentSettingsTypedDict(TypedDict):
    THREADS_RUNS_AVIEW: NotRequired[str]
    THREADS_LIST_VIEW: NotRequired[str]
    MODELS_LIST_VIEW: NotRequired[str]
    DISABLE_ATTACHMENT_UI_BUTTON: NotRequired[bool]
    UPLOAD_PREPROCESS_HANDLER: NotRequired[Optional[str]]
    DEFAULT_MODEL_PROVIDER: NotRequired[str]
    AVAILABLE_MODEL_PROVIDERS: NotRequired[Optional[List[str]]]


class ApplicationsSettingsTypedDict(TypedDict):
    label: str
    version: NotRequired[str]
    description: NotRequired[str]


class ApplicationSettingsTypedDict(TypedDict):
    label: str
    tabs: list[str]