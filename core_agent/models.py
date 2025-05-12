import uuid
import importlib
from django.db import models
from django.apps import apps
from pydantic import BaseModel
from .dataclasses import AgentConfig


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
        agent_queryset = self.filter(metadata__tags__Type__contains=agent_config_tag).order_by('metadata__order')
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
        return agent
    
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


class KnowledgeBase(models.Model):
    id = models.UUIDField(default=uuid.uuid4, unique=True, primary_key=True)
    name = models.CharField(max_length=255)
    metadata = models.JSONField(blank=True, null=True)

    def __str__(self):
        return self.name


class DataSource(models.Model):
    id = models.UUIDField(default=uuid.uuid4, unique=True, primary_key=True)
    name = models.CharField(max_length=255)
    # data_source_config fields:
    # {
    # "type": "GITHUB" | "CUSTOM"
    # "github_config": {
    #   "crawler_config": {
    #     "inclusion_prefixes": ["string",]
    #   },
    #   "source_config": {
    #     "owner": "string",
    #     "repo": "string",
    #     "branch": "string"
    #   }
    # }
    data_source_config = models.JSONField(blank=True, null=True)
    knowledge_base = models.ForeignKey(KnowledgeBase, on_delete=models.CASCADE)
    metadata = models.JSONField(blank=True, null=True)

    def __str__(self):
        return self.name


class Agent(models.Model):
    id = models.UUIDField(default=uuid.uuid4, unique=True, primary_key=True)
    name = models.CharField(max_length=255)
    system_prompt = models.TextField(blank=True)
    knowledge_bases = models.ManyToManyField(KnowledgeBase, related_name='knowledge_bases', blank=True)
    # metadata fields:
    # 'model_name', 'suggested_messages', 'overview_html', 'enable_web_search',
    # 'enable_knowledge_base', 'knowledge_base_id'
    metadata = models.JSONField(blank=True, null=True)

    objects = AgentManager()

    def get_config(self) -> AgentConfig:
        return AgentConfig(
            id=str(self.id),
            label=self.name,
            description=self.metadata.get('description', ''),
            agent_class=self.metadata.get('agent_class', ''),
            prompt_template=self.system_prompt,
            overview_html=self.metadata.get('overview_html', ''),
            model_name=self.metadata.get('model_name', ''),
            enable_web_search=self.metadata.get('enable_web_search', False),
            enable_knowledge_base=self.metadata.get('enable_knowledge_base', False),
            knowledge_bases=list(self.knowledge_bases.all().values()),
            suggested_messages=self.metadata.get('suggested_messages', []),
        )

    def __str__(self):
        return self.name


class DataAutomationInvocation(models.Model):
    class Status(models.TextChoices):
        CREATED = 'created', 'Created'
        IN_PROGRESS = 'in_progress', 'In Progress'
        SUCCESS = 'success', 'Success'
        ERROR = 'error', 'Error'
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.CREATED,
    )
    id = models.UUIDField(default=uuid.uuid4, unique=True, primary_key=True)
    data_automation_project = models.ForeignKey(
        'DataAutomationProject', on_delete=models.CASCADE, related_name='data_automation_project'
    )
    # metadata fields:
    # 'error_message': 'string'
    # 'output_configuration': {
    #     "s3_uri": 'string'
    # }
    metadata = models.JSONField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.data_automation_project.name} - {self.id}"


class Blueprint(models.Model):
    id = models.UUIDField(default=uuid.uuid4, unique=True, primary_key=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    # schema fields:
    """
    {
    "properties": {
        "invoice_number": {
            "type": "string",
            "description": "The unique invoice identifier"
        },
        ...
    }
    """
    schema = models.JSONField(blank=True, null=True)
    metadata = models.JSONField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name
    

class DataAutomationProjectManager(models.Manager):
    def get_user_projects(self, user):
        """
        Returns all DataAutomationProject instances associated with the given user
        through the chain: DataAutomationProject -> account -> contact -> user
        
        Args:
            user: The authenticated user from request.user
            
        Returns:
            QuerySet of DataAutomationProject instances related to the user
        """
        if not user or user.is_anonymous:
            return self.none()
            
        # Follow the relationship chain backward:
        # user -> contact -> account -> project
        return self.filter(
            account__contacts__user=user
        ).distinct()


class DataAutomationProject(models.Model):
    id = models.UUIDField(default=uuid.uuid4, unique=True, primary_key=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    blueprints = models.ManyToManyField(Blueprint, related_name="blueprints", blank=True)
    if apps.is_installed('core_sales'):
        account = models.ForeignKey('core_sales.Account', on_delete=models.CASCADE,
                                    blank=True, null=True)
    metadata = models.JSONField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    projects = DataAutomationProjectManager()

    def __str__(self):
        return self.name