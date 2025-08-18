from typing import TypedDict
from typing_extensions import NotRequired


class AgentSettingsTypedDict(TypedDict):
    THREADS_RUNS_AVIEW: NotRequired[str]
    THREADS_LIST_VIEW: NotRequired[str]
    MODELS_LIST_VIEW: NotRequired[str]


class ApplicationsSettingsTypedDict(TypedDict):
    label: str
    version: NotRequired[str]
    description: NotRequired[str]


class ApplicationSettingsTypedDict(TypedDict):
    label: str
    tabs: list[str]