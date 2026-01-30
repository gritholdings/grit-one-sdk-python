from datetime import datetime
from typing import Any, Dict, Optional


class WorkflowContext:
    def __init__(self):
        self._data: Dict[str, Any] = {}
        self._started_at: str = datetime.now().isoformat()
    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)
    def set(self, key: str, value: Any) -> None:
        self._data[key] = value
    def to_dict(self) -> Dict[str, Any]:
        return {
            "data": self._data.copy(),
            "started_at": self._started_at
        }


class NodeContext:
    def __init__(self, node_id: str, node_name: str = ""):
        self._node_id = node_id
        self._node_name = node_name
        self._data: Dict[str, Any] = {}
        self._executed_at: Optional[str] = None
    @property
    def id(self) -> str:
        return self._node_id
    @property
    def name(self) -> str:
        return self._node_name
    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)
    def set(self, key: str, value: Any) -> None:
        self._data[key] = value
    def mark_executed(self) -> None:
        self._executed_at = datetime.now().isoformat()
    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self._node_id,
            "node_name": self._node_name,
            "data": self._data.copy(),
            "executed_at": self._executed_at
        }
