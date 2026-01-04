"""
Type definitions for workflow execution.

Core workflow configuration types (WorkflowTypedDict, etc.) are defined in
grit.core.types alongside other settings types. This module contains
execution-specific types.
"""
from typing import Dict, Any
from typing_extensions import TypedDict, NotRequired

# Re-export core workflow types for convenience
from grit.core.types import (
    WorkflowTypedDict,
    WorkflowNodeTypedDict,
    WorkflowEdgeTypedDict,
    WorkflowMetaTypedDict,
    WorkflowPositionTypedDict,
)


class WorkflowExecutionResult(TypedDict):
    """Result of a workflow execution."""
    success: bool
    workflow_id: str
    workflow_name: str
    wf: Dict[str, Any]
    nodes: Dict[str, Dict[str, Any]]
    error: NotRequired[str]
