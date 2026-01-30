from abc import ABC, abstractmethod
from typing import Dict, Any
from grit.core.workflows.context import WorkflowContext, NodeContext


class BaseAction(ABC):
    @abstractmethod
    def execute(
        self,
        wf: WorkflowContext,
        nodes: Dict[str, NodeContext],
        node: NodeContext,
        config: Dict[str, Any]
    ) -> None:
        pass
