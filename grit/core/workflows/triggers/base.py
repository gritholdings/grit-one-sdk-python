from abc import ABC, abstractmethod
from typing import Dict, Any
from grit.core.workflows.context import WorkflowContext, NodeContext


class BaseTrigger(ABC):
    @abstractmethod
    def execute(
        self,
        wf: WorkflowContext,
        node: NodeContext,
        config: Dict[str, Any]
    ) -> None:
        pass
