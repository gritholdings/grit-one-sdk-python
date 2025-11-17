"""
MCP (Model Context Protocol) toolset registrations for chatbot_app.

This module registers models for MCP access, allowing internal AI agents
to query them through the /agent/mcp endpoint.
"""

from core_agent.mcp_server import mcp_registry, ModelQueryToolset
from core_agent.models import Agent
from core_sales.models import Account


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
            from core_sales.models import Contact
            contact = Contact.objects.get(user=user)
            query |= Q(account__contacts__user=user)
        except Exception:
            # User has no contact/account - only see public + owned agents
            pass

        return super().get_queryset().filter(query).distinct()


@mcp_registry.register(Account)
class AccountQueryTool(ModelQueryToolset):
    """
    MCP toolset for querying Account records.

    This exposes Account model for read-only queries by AI agents.
    Filters accounts based on user permissions.
    """

    model = Account

    def get_queryset(self):
        """
        Filter accounts based on user access.

        Returns:
            - All accounts for superusers
            - Filtered accounts for regular users (future enhancement)

        For now, returns all accounts for authenticated users.
        Future versions will add permission-based filtering via user_mode manager.
        """
        user = self.request.user

        if user.is_anonymous:
            # Anonymous users see no accounts
            return super().get_queryset().none()

        if user.is_superuser:
            # Superusers see all accounts
            return super().get_queryset()

        # Regular users see all accounts for now
        # Future: Filter based on account contacts/permissions
        return super().get_queryset()
