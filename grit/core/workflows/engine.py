import importlib
from collections import deque
from typing import Dict, Any, List, Type, Union
from grit.core.workflows.context import WorkflowContext, NodeContext
from grit.core.workflows.triggers.base import BaseTrigger
from grit.core.workflows.actions.base import BaseAction
from grit.core.workflows.types import WorkflowTypedDict, WorkflowExecutionResult


class WorkflowEngine:
    def __init__(self, workflow_id: str, config: WorkflowTypedDict):
        self.workflow_id = workflow_id
        self.config = config
        self._node_class_cache: Dict[str, Type[Union[BaseTrigger, BaseAction]]] = {}
    def run(self) -> WorkflowExecutionResult:
        wf = WorkflowContext()
        nodes: Dict[str, NodeContext] = {}
        try:
            execution_order = self._get_execution_order()
            for node_id in execution_order:
                node_config = self.config["nodes"][node_id]
                node = NodeContext(
                    node_id=node_id,
                    node_name=node_config.get("name", "")
                )
                node_class = self._resolve_node_type(node_config["type"])
                node_instance = node_class()
                if isinstance(node_instance, BaseTrigger):
                    node_instance.execute(wf=wf, node=node, config=node_config)
                elif isinstance(node_instance, BaseAction):
                    node_instance.execute(
                        wf=wf, nodes=nodes, node=node, config=node_config
                    )
                node.mark_executed()
                nodes[node_id] = node
            return WorkflowExecutionResult(
                success=True,
                workflow_id=self.workflow_id,
                workflow_name=self.config["meta"]["name"],
                wf=wf.to_dict(),
                nodes={k: v.to_dict() for k, v in nodes.items()}
            )
        except Exception as e:
            return WorkflowExecutionResult(
                success=False,
                workflow_id=self.workflow_id,
                workflow_name=self.config["meta"]["name"],
                wf=wf.to_dict(),
                nodes={k: v.to_dict() for k, v in nodes.items()},
                error=str(e)
            )
    def _get_execution_order(self) -> List[str]:
        nodes = self.config["nodes"]
        edges = self.config.get("edges", {})
        in_degree: Dict[str, int] = {node_id: 0 for node_id in nodes}
        adjacency: Dict[str, List[str]] = {node_id: [] for node_id in nodes}
        for edge in edges.values():
            source = edge["source_node_id"]
            target = edge["target_node_id"]
            adjacency[source].append(target)
            in_degree[target] += 1
        queue = deque([
            node_id for node_id, degree in in_degree.items() if degree == 0
        ])
        execution_order: List[str] = []
        while queue:
            node_id = queue.popleft()
            execution_order.append(node_id)
            for neighbor in adjacency[node_id]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)
        if len(execution_order) != len(nodes):
            raise ValueError(
                f"Workflow '{self.workflow_id}' contains a cycle - "
                "cannot determine execution order"
            )
        return execution_order
    def _resolve_node_type(
        self, type_path: str
    ) -> Type[Union[BaseTrigger, BaseAction]]:
        if type_path in self._node_class_cache:
            return self._node_class_cache[type_path]
        module = importlib.import_module(type_path)
        node_class = None
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if isinstance(attr, type):
                if (
                    issubclass(attr, (BaseTrigger, BaseAction))
                    and attr not in (BaseTrigger, BaseAction)
                ):
                    node_class = attr
                    break
        if node_class is None:
            raise ValueError(
                f"No BaseTrigger or BaseAction subclass found in '{type_path}'"
            )
        self._node_class_cache[type_path] = node_class
        return node_class
