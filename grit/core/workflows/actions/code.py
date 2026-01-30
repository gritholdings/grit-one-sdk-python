from typing import Dict, Any
from grit.core.workflows.context import WorkflowContext, NodeContext
from grit.core.workflows.actions.base import BaseAction


class CodeAction(BaseAction):
    def execute(
        self,
        wf: WorkflowContext,
        nodes: Dict[str, NodeContext],
        node: NodeContext,
        config: Dict[str, Any]
    ) -> None:
        py_code = config.get("py_code", "")
        if not py_code or not py_code.strip():
            return
        exec_globals = {
            "wf": wf,
            "nodes": nodes,
            "node": node,
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
        exec(py_code, exec_globals, exec_locals)
