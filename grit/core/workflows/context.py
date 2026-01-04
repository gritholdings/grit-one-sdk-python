"""
Workflow context classes for managing state during workflow execution.

These classes provide the `wf`, `nodes`, and `node` objects that are
available within py_code execution.
"""
from datetime import datetime
from typing import Any, Dict, Optional


class WorkflowContext:
    """
    Global workflow context accessible via `wf` in py_code.

    Stores workflow-level state that needs to be shared across all nodes.

    Usage in py_code:
        wf.set("final_result", result)
        value = wf.get("final_result")
    """

    def __init__(self):
        self._data: Dict[str, Any] = {}
        self._started_at: str = datetime.now().isoformat()

    def get(self, key: str, default: Any = None) -> Any:
        """Get a value from the workflow context."""
        return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Set a value in the workflow context."""
        self._data[key] = value

    def to_dict(self) -> Dict[str, Any]:
        """Export context as a dictionary."""
        return {
            "data": self._data.copy(),
            "started_at": self._started_at
        }


class NodeContext:
    """
    Node-level context accessible via `node` in py_code.

    Stores output and state for a single node. After execution,
    this node's context becomes available to downstream nodes
    via `nodes["node_id"]`.

    Usage in py_code:
        # Store output for downstream nodes
        node.set("output", processed_data)
        node.set("processed", True)

        # Access from downstream node
        input_data = nodes["n_j3d9"].get("output")
    """

    def __init__(self, node_id: str, node_name: str = ""):
        self._node_id = node_id
        self._node_name = node_name
        self._data: Dict[str, Any] = {}
        self._executed_at: Optional[str] = None

    @property
    def id(self) -> str:
        """The node's unique identifier."""
        return self._node_id

    @property
    def name(self) -> str:
        """The node's display name."""
        return self._node_name

    def get(self, key: str, default: Any = None) -> Any:
        """Get a value from the node context."""
        return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Set a value in the node context."""
        self._data[key] = value

    def mark_executed(self) -> None:
        """Mark this node as executed with current timestamp."""
        self._executed_at = datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        """Export context as a dictionary."""
        return {
            "node_id": self._node_id,
            "node_name": self._node_name,
            "data": self._data.copy(),
            "executed_at": self._executed_at
        }
