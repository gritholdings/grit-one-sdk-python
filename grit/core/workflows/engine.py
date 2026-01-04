"""
Workflow execution engine.

Orchestrates the execution of workflow nodes based on their
configuration and edge connections.
"""
import importlib
from collections import deque
from typing import Dict, Any, List, Type, Union

from grit.core.workflows.context import WorkflowContext, NodeContext
from grit.core.workflows.triggers.base import BaseTrigger
from grit.core.workflows.actions.base import BaseAction
from grit.core.workflows.types import WorkflowTypedDict, WorkflowExecutionResult


class WorkflowEngine:
    """
    Engine for executing workflows defined in configuration.

    The engine:
    1. Parses the workflow configuration
    2. Determines execution order via topological sort
    3. Resolves node types to Python classes
    4. Executes nodes in order, passing context between them

    Usage:
        from grit.core.workflows.engine import WorkflowEngine

        workflow_config = settings.APP_METADATA_SETTINGS['WORKFLOWS']['workflow_1']
        engine = WorkflowEngine(workflow_id='workflow_1', config=workflow_config)
        result = engine.run()
    """

    def __init__(self, workflow_id: str, config: WorkflowTypedDict):
        """
        Initialize the workflow engine.

        Args:
            workflow_id: Unique identifier for this workflow
            config: The workflow configuration dictionary
        """
        self.workflow_id = workflow_id
        self.config = config
        self._node_class_cache: Dict[str, Type[Union[BaseTrigger, BaseAction]]] = {}

    def run(self) -> WorkflowExecutionResult:
        """
        Execute the workflow.

        Returns:
            WorkflowExecutionResult with execution status and context data
        """
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

                # Resolve and instantiate the node type
                node_class = self._resolve_node_type(node_config["type"])
                node_instance = node_class()

                # Execute based on whether it's a trigger or action
                if isinstance(node_instance, BaseTrigger):
                    node_instance.execute(wf=wf, node=node, config=node_config)
                elif isinstance(node_instance, BaseAction):
                    node_instance.execute(
                        wf=wf, nodes=nodes, node=node, config=node_config
                    )

                # Mark node as executed and store in nodes dict
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
        """
        Determine node execution order using topological sort.

        Uses Kahn's algorithm to sort nodes based on edge dependencies.
        Nodes are executed in order where all predecessors complete first.

        Returns:
            List of node IDs in execution order
        """
        nodes = self.config["nodes"]
        edges = self.config.get("edges", {})

        # Build adjacency list and in-degree count
        in_degree: Dict[str, int] = {node_id: 0 for node_id in nodes}
        adjacency: Dict[str, List[str]] = {node_id: [] for node_id in nodes}

        for edge in edges.values():
            source = edge["source_node_id"]
            target = edge["target_node_id"]
            adjacency[source].append(target)
            in_degree[target] += 1

        # Start with nodes that have no incoming edges (triggers)
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

        # Check for cycles
        if len(execution_order) != len(nodes):
            raise ValueError(
                f"Workflow '{self.workflow_id}' contains a cycle - "
                "cannot determine execution order"
            )

        return execution_order

    def _resolve_node_type(
        self, type_path: str
    ) -> Type[Union[BaseTrigger, BaseAction]]:
        """
        Resolve a node type path to its Python class.

        Args:
            type_path: Dot-separated module path, e.g.,
                       'grit.core.workflows.triggers.manual'

        Returns:
            The node class (ManualTrigger, CodeAction, etc.)
        """
        if type_path in self._node_class_cache:
            return self._node_class_cache[type_path]

        # Import the module
        module = importlib.import_module(type_path)

        # Find the class that inherits from BaseTrigger or BaseAction
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
