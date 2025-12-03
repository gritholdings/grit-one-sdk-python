from django.apps import AppConfig


class AgentsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core_agent'
    verbose_name = 'Agents'

    def ready(self):
        """
        Import MCP toolsets and metadata when the app is ready.
        This ensures model registrations are loaded at startup.
        """
        # Import metadata registrations (from chatbot_app) if available
        try:
            from chatbot_app import metadata  # noqa: F401
        except ImportError:
            pass  # metadata.py is optional

        # Import manual MCP toolset registrations (for models with custom logic)
        from . import mcp_tools  # noqa: F401

        # Auto-discover and register models with user_mode managers
        from .mcp_server import mcp_registry
        mcp_registry.auto_discover()
