"""
Base class for workflow actions.

Actions are processing nodes that perform work within a workflow.
Examples: execute code, send HTTP request, update database record.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any

from grit.core.workflows.context import WorkflowContext, NodeContext


class BaseAction(ABC):
    """
    Abstract base class for all workflow actions.

    Subclasses must implement the execute() method which performs
    the action's logic and stores results in the node context.
    """

    @abstractmethod
    def execute(
        self,
        wf: WorkflowContext,
        nodes: Dict[str, NodeContext],
        node: NodeContext,
        config: Dict[str, Any]
    ) -> None:
        """
        Execute the action logic.

        Args:
            wf: The global workflow context for storing shared state
            nodes: Dictionary of previously executed nodes' contexts
            node: This action node's context for storing output
            config: The node configuration from the workflow definition
        """
        pass
