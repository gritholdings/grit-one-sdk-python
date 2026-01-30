from grit.core.core_base_settings import BaseSettings


class AgentSettings(BaseSettings):
    SETTINGS_KEY = 'AGENT_SETTINGS'
    THREADS_RUNS_AVIEW: str = 'grit.agent.aviews.threads_runs'
    THREADS_LIST_VIEW: str = 'grit.agent.views.threads_list'
    MODELS_LIST_VIEW: str = 'grit.agent.views.models_list'
    DISABLE_ATTACHMENT_UI_BUTTON: bool = False
agent_settings: AgentSettings = AgentSettings()