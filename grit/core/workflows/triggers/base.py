"""
Base class for workflow triggers.

Triggers are entry points that start workflow execution.
Examples: manual click, scheduled time, webhook, record update.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any

from grit.core.workflows.context import WorkflowContext, NodeContext


class BaseTrigger(ABC):
    """
    Abstract base class for all workflow triggers.

    Subclasses must implement the execute() method which is called
    when the workflow starts at this trigger node.
    """

    @abstractmethod
    def execute(
        self,
        wf: WorkflowContext,
        node: NodeContext,
        config: Dict[str, Any]
    ) -> None:
        """
        Execute the trigger logic.

        Args:
            wf: The global workflow context for storing shared state
            node: This trigger node's context for storing output
            config: The node configuration from the workflow definition
        """
        pass
