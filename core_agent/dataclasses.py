import importlib
from dataclasses import dataclass, field
from typing import List, Optional, Type


@dataclass
class AgentConfig:
    id: str
    label: str
    description: str
    agent_class: Optional[Type['BaseAgent'] | str] = None
    tags: Optional[List[str]] = field(default_factory=list)
    prompt_template: Optional[str] = None
    enable_web_search: bool = True
    record_usage_for_payment: bool = True
    suggested_messages: Optional[List[str]] = field(default_factory=list)


@dataclass
class AgentConfigs:
    """A container for multiple AgentConfig objects."""
    
    agent_configs: List[AgentConfig] = field(default_factory=list)

    def get_agent_config(self, agent_config_id: str) -> Optional[AgentConfig]:
        """
        Return the `AgentConfig` that matches the given id.
        If no match is found, returns None.
        """
        for agent_config_item in self.agent_configs:
            if agent_config_item.id == agent_config_id:
                return agent_config_item
        return None

    def get_agent_class(self, model_id: str):
        agent_config = self.get_agent_config(model_id)
        if not agent_config or not agent_config.agent_class:
            return None

        # If agent_class is a string, dynamically import
        if isinstance(agent_config.agent_class, str):
            module_path, class_name = agent_config.agent_class.rsplit('.', 1)
            module = importlib.import_module(module_path)
            return getattr(module, class_name)

        # Otherwise return as-is
        return agent_config.agent_class

    def get_agent(self, label: str, *args, **kwargs):
        """
        Instantiate and return an agent for the specified label.
        If no class is found, returns None.
        """
        agent_class = self.get_agent_class(label)
        if agent_class is None:
            return None
        return agent_class(*args, **kwargs)
    
    def list_models(self, tags: Optional[List[str]] = None) -> List[dict]:
        """
        Return a list of dicts representing the agent models.
        If `tags` is provided, only models containing *all* of those tags are returned.
        
        Example structure:
        [
            {
                'id': <id>,
                'label': <label>,
                'description': <description>
            },
            ...
        ]
        """
        # If no tags were passed in, return them all.
        if not tags:
            filtered_models = self.agent_configs
        else:
            # Return only those models that contain all of the requested tags.
            filtered_models = [
                model for model in self.agent_configs
                if all(tag in model.tags for tag in tags)
            ]

        return [
            {
                'id': model.id,
                'label': model.label,
                'description': model.description,
                'suggested_messages': model.suggested_messages
            }
            for model in filtered_models
        ]