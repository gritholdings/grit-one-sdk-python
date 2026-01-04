"""
Manual trigger for workflows.

This trigger is activated when a user clicks to start the workflow
from the UI. It serves as the entry point for manually-triggered workflows.
"""
from datetime import datetime
from typing import Dict, Any

from grit.core.workflows.context import WorkflowContext, NodeContext
from grit.core.workflows.triggers.base import BaseTrigger


class ManualTrigger(BaseTrigger):
    """
    A trigger that starts workflow execution via manual user action.

    When executed, it records the trigger timestamp and marks the
    workflow as manually initiated.

    Usage in workflow config:
        'n_j3d9': {
            'name': 'Click to start',
            'position': {'x': 789, 'y': 101},
            'type': 'grit.core.workflows.triggers.manual',
        }
    """

    def execute(
        self,
        wf: WorkflowContext,
        node: NodeContext,
        config: Dict[str, Any]
    ) -> None:
        """
        Execute the manual trigger.

        Sets up initial workflow state and records trigger metadata.
        """
        triggered_at = datetime.now().isoformat()

        # Store trigger info in the node context for downstream access
        node.set("triggered_at", triggered_at)
        node.set("trigger_type", "manual")

        # Store in workflow globals for convenience
        wf.set("triggered_at", triggered_at)
        wf.set("trigger_type", "manual")
