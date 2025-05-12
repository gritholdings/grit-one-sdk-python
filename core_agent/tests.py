import os
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()

import unittest
from unittest.mock import patch, Mock, MagicMock, call

from .dataclasses import AgentConfigs, AgentConfig
from core.utils.aws.s3 import S3Client
from core.utils.github import GithubClient
from core_agent.agent import BaseAgent
from core_agent.knowledge_base import KnowledgeBaseClient
from .utils import get_computed_system_prompt


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


@patch('core.settings.DATABASE_PASSWORD', 'mocked_password')
@patch('core.settings.AWS_RDS_ENDPOINT', 'mocked_endpoint')
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


class TestUtils(unittest.TestCase):
    def test_get_computed_system_prompt_valid(self):
        """
        Test that get_computed_system_prompt returns the correct prompt when all fields are present.
        """
        metadata = {
            'system_prompt': 'system prompt content',
            'syllabus_info': 'syllabus info content here'
        }
        
        system_prompt = """You are an AI tutor.
Context:
{system_prompt}

also this:
{unknown_variable}
{syllabus_info}
"""

        result = get_computed_system_prompt(system_prompt, metadata)
        self.assertEqual(result, """You are an AI tutor.
Context:
system prompt content

also this:
{unknown_variable}
syllabus info content here
""")


class TestKnowledgeBaseClient(unittest.TestCase):
    
    def setUp(self):
        """Set up test fixtures."""
        self.client = KnowledgeBaseClient(bucket_name="test-bucket")
        
    @patch('core_agent.knowledge_base.requests.get')
    @patch.object(S3Client, 'upload_file_to_s3')
    @patch.object(S3Client, 'list_s3_files_in_prefix')
    @patch.object(S3Client, 'delete_s3_files')
    @patch.object(GithubClient, 'fetch_github_contents')
    def test_upload_github_folder_to_s3(
        self,
        mock_fetch_github_contents,
        mock_delete_s3_files,
        mock_list_s3_files,
        mock_upload_file,
        mock_requests_get
    ):
        """Test the upload_github_folder_to_s3 method."""
        
        # Setup test data
        github_owner = "test-owner"
        github_repo = "test-repo"
        github_folder = "docs"
        github_branch = "develop"
        
        # Mock GitHub API response
        github_files = [
            {
                'path': 'docs/file1.md',
                'download_url': 'https://raw.githubusercontent.com/test-owner/test-repo/develop/docs/file1.md'
            },
            {
                'path': 'docs/subfolder/file2.md',
                'download_url': 'https://raw.githubusercontent.com/test-owner/test-repo/develop/docs/subfolder/file2.md'
            }
        ]
        mock_fetch_github_contents.return_value = github_files
        
        # Mock S3 existing files
        s3_existing_files = [
            'docs/file1.md',
            'docs/subfolder/file2.md',
            'docs/old_file.md'  # This file should be deleted
        ]
        mock_list_s3_files.return_value = s3_existing_files
        
        # Mock HTTP responses for file downloads
        mock_response1 = Mock()
        mock_response1.status_code = 200
        mock_response1.content = b'Content of file1'
        
        mock_response2 = Mock()
        mock_response2.status_code = 200
        mock_response2.content = b'Content of file2'
        
        mock_requests_get.side_effect = [mock_response1, mock_response2]
        
        # Call the method under test
        result = self.client.upload_github_folder_to_s3(
            github_owner=github_owner,
            github_repo=github_repo,
            github_folder=github_folder,
            github_branch=github_branch
        )
        
        # Assert GitHub client was called correctly
        mock_fetch_github_contents.assert_called_once_with(
            owner=github_owner,
            repo=github_repo,
            path=github_folder,
            branch=github_branch
        )
        
        # Assert requests.get was called with correct URLs
        expected_get_calls = [
            call('https://raw.githubusercontent.com/test-owner/test-repo/develop/docs/file1.md'),
            call('https://raw.githubusercontent.com/test-owner/test-repo/develop/docs/subfolder/file2.md')
        ]
        mock_requests_get.assert_has_calls(expected_get_calls, any_order=False)
        
        # Assert S3 uploads were called correctly
        expected_upload_calls = [
            call(b'Content of file1', 'docs/file1.md'),
            call(b'Content of file2', 'docs/subfolder/file2.md')
        ]
        mock_upload_file.assert_has_calls(expected_upload_calls, any_order=False)
        
        # Assert S3 listing was called correctly
        mock_list_s3_files.assert_called_once_with(github_folder)
        
        # Assert S3 deletion was called with the correct file
        mock_delete_s3_files.assert_called_once_with(['docs/old_file.md'])
        
        # Assert the return value is correct
        expected_result = {
            "status": "success",
            "message": "S3 folder synced with GitHub repository folder",
            "total_files_uploaded": 2,
            "files_removed": 1,
        }
        self.assertEqual(result, expected_result)
        
    @patch('core_agent.knowledge_base.requests.get')
    @patch.object(S3Client, 'upload_file_to_s3')
    @patch.object(S3Client, 'list_s3_files_in_prefix')
    @patch.object(GithubClient, 'fetch_github_contents')
    def test_upload_github_folder_to_s3_with_failed_download(
        self,
        mock_fetch_github_contents,
        mock_list_s3_files,
        mock_upload_file,
        mock_requests_get
    ):
        """Test handling of failed file downloads."""
        
        # Mock GitHub API response
        github_files = [
            {
                'path': 'docs/file1.md',
                'download_url': 'https://raw.githubusercontent.com/owner/repo/main/docs/file1.md'
            }
        ]
        mock_fetch_github_contents.return_value = github_files
        
        # Mock HTTP response for failed download
        mock_response = Mock()
        mock_response.status_code = 404  # Not found
        mock_requests_get.return_value = mock_response
        
        # Call the method under test
        with patch('builtins.print') as mock_print:
            result = self.client.upload_github_folder_to_s3(
                github_owner="owner",
                github_repo="repo",
                github_folder="docs"
            )
        
        # Assert upload was not called
        mock_upload_file.assert_not_called()
        
        # Assert error was printed
        mock_print.assert_called_once_with(
            "Failed to download https://raw.githubusercontent.com/owner/repo/main/docs/file1.md "
            "(status code: 404)"
        )
        
        # Assert the return value is correct
        expected_result = {
            "status": "success",
            "message": "S3 folder synced with GitHub repository folder",
            "total_files_uploaded": 1,  # Still counts as processed even though download failed
            "files_removed": 0,
        }
        self.assertEqual(result, expected_result)