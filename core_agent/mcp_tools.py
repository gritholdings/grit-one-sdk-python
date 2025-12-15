"""
MCP (Model Context Protocol) toolset registrations for chatbot_app.

This module contains manual registrations for models that require custom
query filtering logic beyond what the scoped manager provides.

Models with simple permission logic can rely on auto-discovery via the
scoped manager convention. Only register models here if they need
custom get_queryset() implementations.

NOTE: Models with scoped managers are auto-discovered at startup.
Manual registrations in this file override auto-discovered ones.
"""

from core_agent.mcp_server import mcp_registry, ModelQueryToolset
from core_agent.models import Agent


@mcp_registry.register(Agent)
class AgentQueryTool(ModelQueryToolset):
    """
    MCP toolset for querying Agent records.

    This exposes Agent model for read-only queries by AI agents.
    Filters agents based on user permissions and ownership.
    """

    model = Agent

    def get_queryset(self):
        """
        Filter agents based on user access.

        Returns:
            - Public agents (account=null)
            - Private agents belonging to the user's account
            - User's owned agents

        This matches the permission logic in Agent.objects.get_user_agents()
        """
        from django.db.models import Q

        user = self.request.user

        if user.is_anonymous:
            # Anonymous users only see public agents
            return super().get_queryset().filter(account__isnull=True)

        if user.is_superuser:
            # Superusers see all agents
            return super().get_queryset()

        # Authenticated users see:
        # 1. Public agents (account=null)
        # 2. Private agents from their account
        # 3. Agents they own
        query = Q(account__isnull=True) | Q(owner=user)

        # Check if user has an account through Contact
        try:
            from grit.sales.models import Contact
            contact = Contact.objects.get(user=user)
            query |= Q(account__contacts__user=user)
        except Exception:
            # User has no contact/account - only see public + owned agents
            pass

        return super().get_queryset().filter(query).distinct()
