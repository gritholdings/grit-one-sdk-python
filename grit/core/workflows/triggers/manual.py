from datetime import datetime
from typing import Dict, Any
from grit.core.workflows.context import WorkflowContext, NodeContext
from grit.core.workflows.triggers.base import BaseTrigger


class ManualTrigger(BaseTrigger):
    def execute(
        self,
        wf: WorkflowContext,
        node: NodeContext,
        config: Dict[str, Any]
    ) -> None:
        triggered_at = datetime.now().isoformat()
        node.set("triggered_at", triggered_at)
        node.set("trigger_type", "manual")
        wf.set("triggered_at", triggered_at)
        wf.set("trigger_type", "manual")
