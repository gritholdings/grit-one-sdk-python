from core.core_base_settings import BaseSettings


class AgentSettings(BaseSettings):
    """Default agent settings. Can be overridden in app.settings."""
    SETTINGS_KEY = 'AGENT_SETTINGS'

    THREADS_RUNS_AVIEW: str = 'core_agent.aviews.threads_runs'
    THREADS_LIST_VIEW: str = 'core_agent.views.threads_list'
    MODELS_LIST_VIEW: str = 'core_agent.views.models_list'
    DISABLE_ATTACHMENT_UI_BUTTON: bool = False


# Initialize agent settings instance
agent_settings: AgentSettings = AgentSettings()