from typing import List, Optional
from grit.agent.constants import MODEL_PROVIDER_GROUPS
from grit.core.core_base_settings import BaseSettings


class AgentSettings(BaseSettings):
    SETTINGS_KEY = 'AGENT_SETTINGS'
    THREADS_RUNS_AVIEW: str = 'grit.agent.aviews.threads_runs'
    THREADS_LIST_VIEW: str = 'grit.agent.views.threads_list'
    MODELS_LIST_VIEW: str = 'grit.agent.views.models_list'
    DISABLE_ATTACHMENT_UI_BUTTON: bool = False
    KNOWLEDGE_BASE_ROOT: Optional[str] = None
    UPLOAD_PREPROCESS_HANDLER: Optional[str] = None
    DEFAULT_MODEL_PROVIDER: str = 'api'
    AVAILABLE_MODEL_PROVIDERS: Optional[List[str]] = [
        key for key, *_ in MODEL_PROVIDER_GROUPS
    ]
agent_settings: AgentSettings = AgentSettings()