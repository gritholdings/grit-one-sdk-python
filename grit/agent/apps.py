from django.apps import AppConfig


class AgentsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'grit.agent'
    label = 'core_agent'
    verbose_name = 'Agents'
    def ready(self):
        try:
            from app.agent import metadata
        except ImportError:
            pass
        from . import mcp_tools
        from .mcp_server import mcp_registry
        mcp_registry.auto_discover()
