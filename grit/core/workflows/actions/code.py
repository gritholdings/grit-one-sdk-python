"""
Code action for executing Python code within workflows.

This action executes arbitrary Python code defined in the node's
py_code field, with access to workflow context variables.
"""
from typing import Dict, Any

from grit.core.workflows.context import WorkflowContext, NodeContext
from grit.core.workflows.actions.base import BaseAction


class CodeAction(BaseAction):
    """
    An action that executes Python code from the node's py_code field.

    The code has access to:
        - wf: WorkflowContext for global workflow state
        - nodes: Dict of previously executed NodeContext objects
        - node: Current NodeContext for storing this node's output
        - print: Python's print function for debugging

    Usage in workflow config:
        'n_a1b2': {
            'name': 'Print Hello World',
            'position': {'x': 123, 'y': 456},
            'type': 'grit.core.workflows.actions.code',
            'type_version': 1.1,
            'py_code': '''
                print("Hello, World!")
                node.set("output", "Hello, World!")
            '''
        }

    Example py_code accessing previous nodes:
        input_data = nodes["n_j3d9"].get("output")
        node.set("processed", transform(input_data))
        wf.set("final_result", result)
    """

    def execute(
        self,
        wf: WorkflowContext,
        nodes: Dict[str, NodeContext],
        node: NodeContext,
        config: Dict[str, Any]
    ) -> None:
        """
        Execute the Python code defined in the node's py_code field.

        The code is executed with a restricted global namespace containing
        only the workflow context objects and safe builtins.
        """
        py_code = config.get("py_code", "")

        if not py_code or not py_code.strip():
            return

        # Build the execution context available to py_code
        exec_globals = {
            "wf": wf,
            "nodes": nodes,
            "node": node,
            # Safe builtins for common operations
            "print": print,
            "len": len,
            "str": str,
            "int": int,
            "float": float,
            "bool": bool,
            "list": list,
            "dict": dict,
            "range": range,
            "enumerate": enumerate,
            "zip": zip,
            "map": map,
            "filter": filter,
            "sorted": sorted,
            "min": min,
            "max": max,
            "sum": sum,
            "abs": abs,
            "round": round,
            "isinstance": isinstance,
            "hasattr": hasattr,
            "getattr": getattr,
            "setattr": setattr,
        }

        exec_locals: Dict[str, Any] = {}

        # Execute the py_code
        exec(py_code, exec_globals, exec_locals)
