# tests/test_agent_configs.py

import unittest
from unittest.mock import patch, MagicMock

from .dataclasses import AgentConfigs, AgentConfig
from core_agent.agent import BaseAgent

class MockAgent(BaseAgent):
    """A simple mock agent extending the BaseAgent."""
    def __init__(self, *args, **kwargs):
        super().__init__()
        self.args = args
        self.kwargs = kwargs

    def get_agent_config(self):
        return AgentConfig(
            id="test3",
            label="Test Agent 3",
            description="A mock agent for testing",
            agent_class=MockAgent,
            tags=["alpha", "beta"]
        )

class TestAgentConfigs(unittest.TestCase):

    def setUp(self):
        """
        Create a list of AgentConfig objects and initialize AgentConfigs with them.
        """
        self.models = [
            AgentConfig(
                id="test1",
                label="Test Agent 1",
                description="A mock agent for testing",
                agent_class=MockAgent,
                tags=["alpha", "beta"]
            ),
            AgentConfig(
                id="test2",
                label="Test Agent 2",
                description="Another mock agent",
                agent_class="some_module.SomeAgentClass",
                tags=["alpha"]
            )
        ]
        self.agent_configs = AgentConfigs(agent_configs=self.models)

    def test_get_agent_config_found(self):
        """
        Test that get_agent_config returns the correct AgentConfig when it exists.
        """
        model = self.agent_configs.get_agent_config("test1")
        self.assertIsNotNone(model)
        self.assertEqual(model.id, "test1")
        self.assertEqual(model.label, "Test Agent 1")

    def test_get_agent_config_not_found(self):
        """
        Test that get_agent_config returns None when an AgentConfig doesn't exist.
        """
        model = self.agent_configs.get_agent_config("nonexistent")
        self.assertIsNone(model)

    def test_get_agent_class_direct_reference(self):
        """
        Test that get_agent_class returns the class when agent_class is directly referenced.
        """
        agent_cls = self.agent_configs.get_agent_class("test1")
        self.assertEqual(agent_cls, MockAgent)

    @patch("importlib.import_module")
    def test_get_agent_class_string_import(self, mock_import_module):
        """
        Test that get_agent_class correctly imports and returns a class when agent_class is a string.
        """
        # Set up the mock import to return a module that has a SomeAgentClass attribute
        mock_agent_class = MagicMock()
        mock_module = MagicMock()
        mock_module.SomeAgentClass = mock_agent_class
        mock_import_module.return_value = mock_module

        agent_cls = self.agent_configs.get_agent_class("test2")

        # Verify that import_module was called with the correct path
        mock_import_module.assert_called_once_with("some_module")
        # Verify that the returned class is what we expect
        self.assertEqual(agent_cls, mock_agent_class)

    def test_get_agent_instantiation(self):
        """
        Test that get_agent returns an instance of the correct class with provided args/kwargs.
        """
        agent_instance = self.agent_configs.get_agent("test1", foo="bar")
        self.assertIsInstance(agent_instance, MockAgent)
        self.assertIn("foo", agent_instance.kwargs)
        self.assertEqual(agent_instance.kwargs["foo"], "bar")

    def test_list_models_no_tags(self):
        """
        Test that list_models returns all models when no tags are provided.
        """
        result = self.agent_configs.list_models()
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["id"], "test1")
        self.assertEqual(result[1]["id"], "test2")

    def test_list_models_with_tags(self):
        """
        Test that list_models returns only models matching the provided tags.
        """
        # Looking for all models containing the 'beta' tag
        result = self.agent_configs.list_models(tags=["beta"])
        # Only the first model ('test1') has 'beta'
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["id"], "test1")

    def test_list_models_tags_no_match(self):
        """
        Test that list_models returns an empty list if no models match the provided tags.
        """
        result = self.agent_configs.list_models(tags=["gamma"])  # none has gamma
        self.assertEqual(len(result), 0)


if __name__ == "__main__":
    unittest.main()