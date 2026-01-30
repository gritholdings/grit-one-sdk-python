from .mcp_server import mcp_registry, ModelQueryToolset
from .models import Agent
@mcp_registry.register(Agent)


class AgentQueryTool(ModelQueryToolset):
    model = Agent
    def get_queryset(self):
        from django.db.models import Q
        user = self.request.user
        if user.is_anonymous:
            return super().get_queryset().filter(account__isnull=True)
        if user.is_superuser:
            return super().get_queryset()
        query = Q(account__isnull=True) | Q(owner=user)
        try:
            from grit.sales.models import Contact
            contact = Contact.objects.get(user=user)
            query |= Q(account__contacts__user=user)
        except Exception:
            pass
        return super().get_queryset().filter(query).distinct()
