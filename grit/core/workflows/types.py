from typing import Dict, Any
from typing_extensions import TypedDict, NotRequired
from grit.core.types import (
    WorkflowTypedDict,
    WorkflowNodeTypedDict,
    WorkflowEdgeTypedDict,
    WorkflowMetaTypedDict,
    WorkflowPositionTypedDict,
)


class WorkflowExecutionResult(TypedDict):
    success: bool
    workflow_id: str
    workflow_name: str
    wf: Dict[str, Any]
    nodes: Dict[str, Dict[str, Any]]
    error: NotRequired[str]
