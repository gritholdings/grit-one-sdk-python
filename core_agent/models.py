import uuid
import importlib
from django.db import models
from pydantic import BaseModel


class AgentResponse(BaseModel):
    id: str
    label: str
    description: str
    suggested_messages: list
    overview_html: str


class AgentDetail(BaseModel):
    id: str
    name: str
    system_prompt: str
    suggested_messages: list
    overview_html: str
    enable_web_search: bool
    enable_knowledge_base: bool
    knowledge_base_id: str
    description: str
    agent_class: str
    metadata: dict


class AgentManager(models.Manager):
    def get_agents(self, agent_config_tag: str):
        """
        Returns a list of agents that match the given tag.
        """
        agent_queryset = self.filter(metadata__tags__Type__contains=agent_config_tag).order_by('name')
        agent_responses = [
            AgentResponse(**{
                "id": str(agent.id),
                "label": agent.name,
                "description": agent.metadata.get('description', ''),
                "suggested_messages": agent.metadata.get('suggested_messages', []),
                "overview_html": agent.metadata.get('overview_html', ''),
            })
            for agent in agent_queryset
        ]
        return agent_responses
    
    def get_agent(self, agent_id: str):
        """
        Returns a single agent by ID.
        """
        agent = self.get(id=agent_id)
        agent_detail = AgentDetail(**{
            "id": str(agent.id),
            "name": agent.name,
            "system_prompt": agent.system_prompt,
            "suggested_messages": agent.metadata.get('suggested_messages', []),
            "overview_html": agent.metadata.get('overview_html', ''),
            "enable_web_search": agent.metadata.get('enable_web_search', False),
            "enable_knowledge_base": agent.metadata.get('enable_knowledge_base', False),
            "knowledge_base_id": agent.metadata.get('knowledge_base_id', ''),
            "description": agent.metadata.get('description', ''),
            "agent_class": agent.metadata.get('agent_class', ''),
            "metadata": agent.metadata,
        })
        return agent_detail
    
    def get_agent_class(self, agent_class_str: str):
        if not agent_class_str:
            return None

        # If agent_class is a string, dynamically import
        if isinstance(agent_class_str, str):
            module_path, class_name = agent_class_str.rsplit('.', 1)
            module = importlib.import_module(module_path)
            return getattr(module, class_name)

        # Otherwise return as-is
        return agent_class_str


class Agent(models.Model):
    id = models.UUIDField(default=uuid.uuid4, unique=True, primary_key=True)
    name = models.CharField(max_length=255)
    system_prompt = models.TextField(blank=True)
    # metadata fields:
    # 'suggested_messages', 'overview_html', 'enable_web_search',
    # 'enable_knowledge_base', 'knowledge_base_id'
    metadata = models.JSONField(blank=True, null=True)

    objects = AgentManager()

    def __str__(self):
        return self.name