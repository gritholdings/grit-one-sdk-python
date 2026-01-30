from django.test import TestCase
from grit.core.workflows.context import WorkflowContext, NodeContext
from grit.core.workflows.engine import WorkflowEngine
from grit.core.workflows.triggers.manual import ManualTrigger
from grit.core.workflows.actions.code import CodeAction


class WorkflowContextTests(TestCase):
    def test_set_and_get(self):
        wf = WorkflowContext()
        wf.set("key", "value")
        self.assertEqual(wf.get("key"), "value")
    def test_get_default(self):
        wf = WorkflowContext()
        self.assertIsNone(wf.get("nonexistent"))
        self.assertEqual(wf.get("nonexistent", "default"), "default")
    def test_to_dict(self):
        wf = WorkflowContext()
        wf.set("key", "value")
        result = wf.to_dict()
        self.assertIn("data", result)
        self.assertIn("started_at", result)
        self.assertEqual(result["data"]["key"], "value")


class NodeContextTests(TestCase):
    def test_set_and_get(self):
        node = NodeContext("node_1", "Test Node")
        node.set("output", {"result": 42})
        self.assertEqual(node.get("output"), {"result": 42})
    def test_properties(self):
        node = NodeContext("node_1", "Test Node")
        self.assertEqual(node.id, "node_1")
        self.assertEqual(node.name, "Test Node")
    def test_mark_executed(self):
        node = NodeContext("node_1", "Test Node")
        self.assertIsNone(node._executed_at)
        node.mark_executed()
        self.assertIsNotNone(node._executed_at)


class ManualTriggerTests(TestCase):
    def test_execute(self):
        wf = WorkflowContext()
        node = NodeContext("trigger_1", "Manual Trigger")
        trigger = ManualTrigger()
        trigger.execute(wf=wf, node=node, config={})
        self.assertIsNotNone(node.get("triggered_at"))
        self.assertEqual(node.get("trigger_type"), "manual")
        self.assertEqual(wf.get("trigger_type"), "manual")


class CodeActionTests(TestCase):
    def test_execute_simple_code(self):
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
        self.assertEqual(node.get("result"), 2)
        self.assertTrue(wf.get("calculated"))
    def test_execute_with_previous_nodes(self):
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
        self.assertEqual(node.get("result"), "HELLO")
    def test_execute_empty_code(self):
        wf = WorkflowContext()
        nodes = {}
        node = NodeContext("code_1", "Code Action")
        action = CodeAction()
        action.execute(wf=wf, nodes=nodes, node=node, config={"py_code": ""})
        action.execute(wf=wf, nodes=nodes, node=node, config={"py_code": "   "})
        action.execute(wf=wf, nodes=nodes, node=node, config={})


class WorkflowEngineTests(TestCase):
    def test_simple_workflow(self):
        config = {
            "meta": {"name": "Test Workflow"},
            "nodes": {
                "trigger": {
                    "name": "Start",
                    "position": {"x": 0, "y": 0},
                    "type": "grit.core.workflows.triggers.manual"
                },
                "action": {
                    "name": "Process",
                    "position": {"x": 100, "y": 0},
                    "type": "grit.core.workflows.actions.code",
                    "py_code": "node.set('result', 'processed')"
                }
            },
            "edges": {
                "e1": {
                    "source_node_id": "trigger",
                    "target_node_id": "action"
                }
            }
        }
        engine = WorkflowEngine(workflow_id="test", config=config)
        result = engine.run()
        self.assertTrue(result["success"])
        self.assertEqual(result["workflow_name"], "Test Workflow")
        self.assertEqual(
            result["nodes"]["action"]["data"]["result"],
            "processed"
        )
    def test_execution_order(self):
        config = {
            "meta": {"name": "Order Test"},
            "nodes": {
                "a": {
                    "name": "A",
                    "position": {"x": 0, "y": 0},
                    "type": "grit.core.workflows.triggers.manual"
                },
                "b": {
                    "name": "B",
                    "position": {"x": 100, "y": 0},
                    "type": "grit.core.workflows.actions.code",
                    "py_code": "node.set('order', 1)"
                },
                "c": {
                    "name": "C",
                    "position": {"x": 200, "y": 0},
                    "type": "grit.core.workflows.actions.code",
                    "py_code": "node.set('order', nodes['b'].get('order') + 1)"
                }
            },
            "edges": {
                "e1": {"source_node_id": "a", "target_node_id": "b"},
                "e2": {"source_node_id": "b", "target_node_id": "c"}
            }
        }
        engine = WorkflowEngine(workflow_id="test", config=config)
        result = engine.run()
        self.assertTrue(result["success"])
        self.assertEqual(result["nodes"]["b"]["data"]["order"], 1)
        self.assertEqual(result["nodes"]["c"]["data"]["order"], 2)
    def test_workflow_error_handling(self):
        config = {
            "meta": {"name": "Error Test"},
            "nodes": {
                "trigger": {
                    "name": "Start",
                    "position": {"x": 0, "y": 0},
                    "type": "grit.core.workflows.triggers.manual"
                },
                "error_node": {
                    "name": "Error",
                    "position": {"x": 100, "y": 0},
                    "type": "grit.core.workflows.actions.code",
                    "py_code": "raise ValueError('Test error')"
                }
            },
            "edges": {
                "e1": {
                    "source_node_id": "trigger",
                    "target_node_id": "error_node"
                }
            }
        }
        engine = WorkflowEngine(workflow_id="test", config=config)
        result = engine.run()
        self.assertFalse(result["success"])
        self.assertIn("error", result)
        self.assertIn("Test error", result["error"])
