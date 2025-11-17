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
        # Import metadata registrations (from chatbot_app)
        from chatbot_app import metadata  # noqa: F401

        # Import MCP toolset registrations
        from . import mcp_tools  # noqa: F401
