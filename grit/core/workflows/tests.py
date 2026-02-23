from grit.core.workflows.context import WorkflowContext, NodeContext
from grit.core.workflows.engine import WorkflowEngine
from grit.core.workflows.triggers.manual import ManualTrigger
from grit.core.workflows.actions.code import CodeAction


def test_context_set_and_get():
    wf = WorkflowContext()
    wf.set("key", "value")
    assert wf.get("key") == "value"


def test_context_get_default():
    wf = WorkflowContext()
    assert wf.get("nonexistent") is None
    assert wf.get("nonexistent", "default") == "default"


def test_context_to_dict():
    wf = WorkflowContext()
    wf.set("key", "value")
    result = wf.to_dict()
    assert "data" in result
    assert "started_at" in result
    assert result["data"]["key"] == "value"


def test_node_set_and_get():
    node = NodeContext("node_1", "Test Node")
    node.set("output", {"result": 42})
    assert node.get("output") == {"result": 42}


def test_node_properties():
    node = NodeContext("node_1", "Test Node")
    assert node.id == "node_1"
    assert node.name == "Test Node"


def test_node_mark_executed():
    node = NodeContext("node_1", "Test Node")
    assert node._executed_at is None
    node.mark_executed()
    assert node._executed_at is not None


def test_manual_trigger_execute():
    wf = WorkflowContext()
    node = NodeContext("trigger_1", "Manual Trigger")
    trigger = ManualTrigger()
    trigger.execute(wf=wf, node=node, config={})
    assert node.get("triggered_at") is not None
    assert node.get("trigger_type") == "manual"
    assert wf.get("trigger_type") == "manual"


def test_code_action_execute_simple():
    wf = WorkflowContext()
    nodes = {}
    node = NodeContext("code_1", "Code Action")
    action = CodeAction()
    config = {
        "py_code": """
node.set("result", 1 + 1)
wf.set("calculated", True)
"""
    }
    action.execute(wf=wf, nodes=nodes, node=node, config=config)
    assert node.get("result") == 2
    assert wf.get("calculated") is True


def test_code_action_with_previous_nodes():
    wf = WorkflowContext()
    prev_node = NodeContext("prev_1", "Previous")
    prev_node.set("output", "hello")
    nodes = {"prev_1": prev_node}
    node = NodeContext("code_1", "Code Action")
    action = CodeAction()
    config = {
        "py_code": """
input_val = nodes["prev_1"].get("output")
node.set("result", input_val.upper())
"""
    }
    action.execute(wf=wf, nodes=nodes, node=node, config=config)
    assert node.get("result") == "HELLO"


def test_code_action_execute_empty():
    wf = WorkflowContext()
    nodes = {}
    node = NodeContext("code_1", "Code Action")
    action = CodeAction()
    action.execute(wf=wf, nodes=nodes, node=node, config={"py_code": ""})
    action.execute(wf=wf, nodes=nodes, node=node, config={"py_code": "   "})
    action.execute(wf=wf, nodes=nodes, node=node, config={})


def test_engine_simple_workflow():
    config = {
        "meta": {"name": "Test Workflow"},
        "nodes": {
            "trigger": {
                "name": "Start",
                "position": {"x": 0, "y": 0},
                "type": "grit.core.workflows.triggers.manual",
            },
            "action": {
                "name": "Process",
                "position": {"x": 100, "y": 0},
                "type": "grit.core.workflows.actions.code",
                "py_code": "node.set('result', 'processed')",
            },
        },
        "edges": {
            "e1": {
                "source_node_id": "trigger",
                "target_node_id": "action",
            }
        },
    }
    engine = WorkflowEngine(workflow_id="test", config=config)
    result = engine.run()
    assert result["success"] is True
    assert result["workflow_name"] == "Test Workflow"
    assert result["nodes"]["action"]["data"]["result"] == "processed"


def test_engine_execution_order():
    config = {
        "meta": {"name": "Order Test"},
        "nodes": {
            "a": {
                "name": "A",
                "position": {"x": 0, "y": 0},
                "type": "grit.core.workflows.triggers.manual",
            },
            "b": {
                "name": "B",
                "position": {"x": 100, "y": 0},
                "type": "grit.core.workflows.actions.code",
                "py_code": "node.set('order', 1)",
            },
            "c": {
                "name": "C",
                "position": {"x": 200, "y": 0},
                "type": "grit.core.workflows.actions.code",
                "py_code": "node.set('order', nodes['b'].get('order') + 1)",
            },
        },
        "edges": {
            "e1": {"source_node_id": "a", "target_node_id": "b"},
            "e2": {"source_node_id": "b", "target_node_id": "c"},
        },
    }
    engine = WorkflowEngine(workflow_id="test", config=config)
    result = engine.run()
    assert result["success"] is True
    assert result["nodes"]["b"]["data"]["order"] == 1
    assert result["nodes"]["c"]["data"]["order"] == 2


def test_engine_error_handling():
    config = {
        "meta": {"name": "Error Test"},
        "nodes": {
            "trigger": {
                "name": "Start",
                "position": {"x": 0, "y": 0},
                "type": "grit.core.workflows.triggers.manual",
            },
            "error_node": {
                "name": "Error",
                "position": {"x": 100, "y": 0},
                "type": "grit.core.workflows.actions.code",
                "py_code": "raise ValueError('Test error')",
            },
        },
        "edges": {
            "e1": {
                "source_node_id": "trigger",
                "target_node_id": "error_node",
            }
        },
    }
    engine = WorkflowEngine(workflow_id="test", config=config)
    result = engine.run()
    assert result["success"] is False
    assert "error" in result
    assert "Test error" in result["error"]
