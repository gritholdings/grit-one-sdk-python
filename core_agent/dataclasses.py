import importlib
from dataclasses import dataclass, field
from typing import List, Optional, Type
from core_agent.agent import BaseAgent


@dataclass
class AgentModel:
    id: str
    label: str
    description: str
    agent_class: Optional[Type[BaseAgent] | str] = None
    tags: Optional[List[str]] = field(default_factory=list)


@dataclass
class AgentModels:
    """A container for multiple AgentModel objects."""
    
    agent_models: List[AgentModel] = field(default_factory=list)

    def get_agent_model(self, model_id: str) -> Optional[AgentModel]:
        """
        Return the `AgentModel` that matches the given id.
        If no match is found, returns None.
        """
        for model in self.agent_models:
            if model.id == model_id:
                return model
        return None

    def get_agent_class(self, model_id: str) -> Optional[Type[BaseAgent]]:
        agent_model = self.get_agent_model(model_id)
        if not agent_model or not agent_model.agent_class:
            return None

        # If agent_class is a string, dynamically import
        if isinstance(agent_model.agent_class, str):
            module_path, class_name = agent_model.agent_class.rsplit('.', 1)
            module = importlib.import_module(module_path)
            return getattr(module, class_name)

        # Otherwise return as-is
        return agent_model.agent_class

    def get_agent(self, label: str, *args, **kwargs) -> Optional[BaseAgent]:
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
            filtered_models = self.agent_models
        else:
            # Return only those models that contain all of the requested tags.
            filtered_models = [
                model for model in self.agent_models
                if all(tag in model.tags for tag in tags)
            ]

        return [
            {
                'id': model.id,
                'label': model.label,
                'description': model.description,
                # 'agent_class': model.agent_class.__name__ if model.agent_class else None
            }
            for model in filtered_models
        ]