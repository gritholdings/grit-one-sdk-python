import importlib
from django.db import models
from django.apps import apps
from django.template import Template, Context
from django.utils import timezone
from pydantic import BaseModel as PydanticBaseModel
from grit.core.db.models import BaseModel
from .extensions.handoff_prompt import RECOMMENDED_PROMPT_PREFIX
from .dataclasses import AgentConfig


class AgentResponse(PydanticBaseModel):
    id: str
    label: str
    description: str
    suggested_messages: list
    overview_html: str


class AgentDetail(PydanticBaseModel):
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
                "description": agent.metadata.get('description', '') if agent.metadata else '',
                "suggested_messages": agent.metadata.get('suggested_messages', []) if agent.metadata else [],
                "overview_html": agent.metadata.get('overview_html', '') if agent.metadata else '',
            })
            for agent in agent_queryset
        ]
        return agent_responses
    
    def get_user_agents(self, user, agent_config_tag: str = None):
        """
        Returns agents accessible to the given user.
        This includes:
        - Public agents (account=null) that match the agent_config_tag
        - Private agents belonging to the user's account
        
        Args:
            user: The authenticated user
            agent_config_tag: Optional tag filter for public agents
            
        Returns:
            List of AgentResponse objects
        """
        if not user or user.is_anonymous:
            # Anonymous users only see public agents with matching tag
            if agent_config_tag:
                agent_queryset = self.filter(
                    account__isnull=True,
                    metadata__tags__Type__contains=agent_config_tag
                ).order_by('metadata__order')
            else:
                return []
        else:
            # Authenticated users see both public and private agents
            from django.db.models import Q
            
            # Start with private agents for user's account
            query = Q(account__contacts__user=user)
            
            # Add public agents with matching tag
            if agent_config_tag:
                query |= Q(account__isnull=True, metadata__tags__Type__contains=agent_config_tag)
            else:
                # If no tag specified, include all public agents
                query |= Q(account__isnull=True)
            
            agent_queryset = self.filter(query).distinct().order_by('metadata__order')

        agent_responses = [
            AgentResponse(**{
                "id": str(agent.id),
                "label": agent.name,
                "description": agent.metadata.get('description', '') if agent.metadata else '',
                "suggested_messages": agent.metadata.get('suggested_messages', []) if agent.metadata else [],
                "overview_html": agent.metadata.get('overview_html', '') if agent.metadata else '',
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
    
    def get_agent_by_name(self, agent_name: str):
        """
        Returns a single agent by name.
        """
        try:
            agent = self.get(name=agent_name)
            return agent
        except self.model.DoesNotExist:
            return None
    
    def get_agent_class(self, agent_class_str: str, model_name: str = None):
        if not agent_class_str:
            # Auto-detect agent class based on model name if not explicitly set
            if model_name and model_name.startswith('claude'):
                agent_class_str = "grit.agent.claude_agent.BaseClaudeAgent"
            else:
                # Default to OpenAI agent class for empty string or None
                agent_class_str = "grit.agent.openai_agent.BaseOpenAIAgent"

        # If agent_class is a string, dynamically import
        if isinstance(agent_class_str, str):
            module_path, class_name = agent_class_str.rsplit('.', 1)
            module = importlib.import_module(module_path)
            return getattr(module, class_name)

        # Otherwise return as-is
        return agent_class_str
    
    def get_agent_config(self, agent_id: str) -> AgentConfig:
        """
        Returns the AgentConfig for the specified agent ID.
        
        Args:
            agent_id: The ID of the agent
            
        Returns:
            AgentConfig object containing agent details
        """
        try:
            agent = self.get(id=agent_id)
            return agent.get_config()
        except self.model.DoesNotExist:
            return None

    def get_sub_agents(self, agent_id: str) -> models.QuerySet:
        """
        Returns sub-agents of the specified agent.

        Args:
            agent_id: The ID of the parent agent

        Returns:
            QuerySet of Agent objects that are sub-agents
        """
        try:
            parent_agent = self.get(id=agent_id)
            return parent_agent.sub_agents.all()
        except self.model.DoesNotExist:
            return self.none()

    def get_formatted_prompt_template(self, agent_id: str, context: dict) -> str:
        """
        Returns the formatted prompt template for the specified agent.

        Args:
            agent_id: The ID of the agent
            context: Additional context dict to merge with default context

        Returns:
            Formatted prompt template string
        """
        agent = self.get(id=agent_id)
        timezone_now = timezone.localtime(timezone.now())
        context_dict = {
            'current_datetime': timezone_now.strftime('%Y-%m-%d %H:%M:%S'),
            'current_date': timezone_now.strftime('%Y-%m-%d'),
            'recommended_prompt_prefix': RECOMMENDED_PROMPT_PREFIX,
        }

        # Merge incoming context with our context_dict
        # Incoming context values will override defaults if keys conflict
        if context:
            context_dict.update(context)

        context_obj = Context(context_dict)
        template = Template(agent.system_prompt)
        formatted_prompt_template = template.render(context_obj)

        # Prepare handoff instructions if sub-agents exist
        handoff_instructions = ""
        sub_agents = self.get_sub_agents(agent_id)
        if sub_agents.exists():
            handoff_instructions = "\n\n# Handoff Instructions\n"
            handoff_instructions += "You can transfer conversations to specialized agents when appropriate. "
            handoff_instructions += "Available agents:\n"
            for sub_agent in sub_agents:
                description = sub_agent.metadata.get('description', '') if sub_agent.metadata else ''
                handoff_instructions += f"- {sub_agent.name}: {description}\n"
            handoff_instructions += "\nWhen you determine a handoff is needed, simply indicate which agent should handle the request."

        return formatted_prompt_template + handoff_instructions


class KnowledgeBase(BaseModel):
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name


class DataSource(BaseModel):
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

    def __str__(self):
        return self.name


class OwnedAgentQuerySet(models.QuerySet):
    def for_owner(self, owner)  :
        """Agents accessible by a specific owner"""
        return self.filter(owner=owner)


class OwnedAgentManager(models.Manager):
    def for_user(self, user_id):
        """
        Get all agents for a user.
        This includes both owned and shared agents.
        """
        from grit.auth.models import CustomUser
        try:
            # user_id can be either a UUID object or a string
            user = CustomUser.objects.get(id=user_id)
            return self.get_queryset().for_owner(owner=user)
        except CustomUser.DoesNotExist:
            return self.none()

    def get_agent(self, agent_id) :
        """Get a specific agent by ID"""
        return self.get_queryset().get(id=agent_id)


class Agent(BaseModel):
    name = models.CharField(max_length=255)
    system_prompt = models.TextField(blank=True)
    knowledge_bases = models.ManyToManyField(KnowledgeBase, related_name='knowledge_bases', blank=True)
    sub_agents = models.ManyToManyField('self', symmetrical=False, related_name='parent_agents', blank=True)
    if apps.is_installed('grit.sales'):
        account = models.ForeignKey('core_sales.Account', on_delete=models.CASCADE,
                                    blank=True, null=True)
    # metadata fields:
    # 'model_name', 'suggested_messages', 'overview_html', 'enable_web_search',
    # 'enable_knowledge_base', 'knowledge_base_id', 'reasoning_effort'

    objects = AgentManager()
    owned = OwnedAgentManager.from_queryset(OwnedAgentQuerySet)()

    def _get_metadata_value(self, key, default=None):
        """Safely get a value from metadata with a default."""
        return self.metadata.get(key, default) if self.metadata else default

    def get_config(self) -> AgentConfig:
        return AgentConfig(
            id=str(self.id),
            label=self.name,
            description=self._get_metadata_value('description', ''),
            agent_class=self._get_metadata_value('agent_class', ''),
            prompt_template=self.system_prompt,
            overview_html=self._get_metadata_value('overview_html', ''),
            model_name=self._get_metadata_value('model_name', ''),
            enable_web_search=self._get_metadata_value('enable_web_search', False),
            enable_knowledge_base=self._get_metadata_value('enable_knowledge_base', False),
            knowledge_bases=list(self.knowledge_bases.all().values()),
            suggested_messages=self._get_metadata_value('suggested_messages', []),
            reasoning_effort=self._get_metadata_value('reasoning_effort'),
        )

    def __str__(self):
        return self.name


class DataAutomationInvocation(BaseModel):
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
    data_automation_project = models.ForeignKey(
        'DataAutomationProject', on_delete=models.CASCADE, related_name='data_automation_project'
    )
    # metadata fields:
    # 'error_message': 'string'
    # 'output_configuration': {
    #     "s3_uri": 'string'
    # }

    def __str__(self):
        return f"{self.data_automation_project.name} - {self.id}"


class Blueprint(BaseModel):
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


class DataAutomationProject(BaseModel):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    blueprints = models.ManyToManyField(Blueprint, related_name="blueprints", blank=True)
    if apps.is_installed('grit.sales'):
        account = models.ForeignKey('core_sales.Account', on_delete=models.CASCADE,
                                    blank=True, null=True)

    projects = DataAutomationProjectManager()

    def __str__(self):
        return self.name