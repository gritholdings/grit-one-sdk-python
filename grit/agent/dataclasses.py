import importlib
from dataclasses import dataclass, field
from typing import List, Optional, Type
@dataclass


class AgentConfig:
    id: str
    label: str
    description: str
    agent_class: Optional[Type['BaseAgent'] | str] = None
    model_name: Optional[str] = None
    tags: Optional[List[str]] = field(default_factory=list)
    prompt_template: Optional[str] = None
    overview_html: Optional[str] = None
    enable_web_search: bool = True
    enable_knowledge_base: bool = False
    knowledge_bases: Optional[List[str]] = field(default_factory=list)
    record_usage_for_payment: bool = True
    suggested_messages: Optional[List[str]] = field(default_factory=list)
    reasoning_effort: Optional[str] = None
@dataclass


class AgentConfigs:
    agent_configs: List[AgentConfig] = field(default_factory=list)
    def get_agent_config(self, agent_config_id: str) -> Optional[AgentConfig]:
        for agent_config_item in self.agent_configs:
            if agent_config_item.id == agent_config_id:
                return agent_config_item
        return None
    def get_agent_class(self, model_id: str):
        agent_config = self.get_agent_config(model_id)
        if not agent_config or not agent_config.agent_class:
            return None
        if isinstance(agent_config.agent_class, str):
            module_path, class_name = agent_config.agent_class.rsplit('.', 1)
            module = importlib.import_module(module_path)
            return getattr(module, class_name)
        return agent_config.agent_class
    def get_agent(self, label: str, *args, **kwargs):
        agent_class = self.get_agent_class(label)
        if agent_class is None:
            return None
        return agent_class(*args, **kwargs)
    def list_models(self, tags: Optional[List[str]] = None) -> List[dict]:
        if not tags:
            filtered_models = self.agent_configs
        else:
            filtered_models = [
                model for model in self.agent_configs
                if all(tag in model.tags for tag in tags)
            ]
        return [
            {
                'id': model.id,
                'label': model.label,
                'description': model.description,
                'suggested_messages': model.suggested_messages,
                'overview_html': model.overview_html,
            }
            for model in filtered_models
        ]