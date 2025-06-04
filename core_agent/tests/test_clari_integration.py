import os
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()

import json
import unittest
from unittest.mock import patch, Mock, MagicMock
from datetime import datetime

from core_agent.third_party.clari import ClariAPIClient, ClariConfig, ClariAPIError, get_secret_value
from core_agent.third_party.clari_data_automation import ClariDataAutomationService
from core_agent.third_party.clari_blueprints import (
    CLARI_CALL_SUMMARY_BLUEPRINT,
    CLARI_TRANSCRIPT_TEXT_BLUEPRINT,
    get_blueprint_by_name,
    list_available_blueprints
)


class TestClariAPIClient(unittest.TestCase):
    """Test the Clari API client functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_account = Mock()
        self.mock_account.metadata = {
            'secrets': [
                {'key': 'CLARI_API_KEY', 'value': 'test_api_key'},
                {'key': 'CLARI_API_PASSWORD', 'value': 'test_api_password'}
            ]
        }
    
    def test_get_secret_value(self):
        """Test the get_secret_value helper function."""
        # Test successful secret retrieval
        api_key = get_secret_value(self.mock_account, 'CLARI_API_KEY')
        self.assertEqual(api_key, 'test_api_key')
        
        # Test non-existent secret
        missing_key = get_secret_value(self.mock_account, 'NON_EXISTENT_KEY')
        self.assertIsNone(missing_key)
        
        # Test with account that has no metadata
        empty_account = Mock()
        empty_account.metadata = None
        result = get_secret_value(empty_account, 'CLARI_API_KEY')
        self.assertIsNone(result)
    
    def test_clari_client_initialization(self):
        """Test ClariAPIClient initialization with account secrets."""
        client = ClariAPIClient(self.mock_account)
        
        self.assertEqual(client.config.api_key, 'test_api_key')
        self.assertEqual(client.config.api_password, 'test_api_password')
        self.assertEqual(client.headers['X-Api-Key'], 'test_api_key')
        self.assertEqual(client.headers['X-Api-Password'], 'test_api_password')
    
    def test_clari_client_missing_credentials(self):
        """Test ClariAPIClient with missing credentials raises error."""
        account_no_secrets = Mock()
        account_no_secrets.metadata = {'secrets': []}
        
        with self.assertRaises(ClariAPIError) as context:
            ClariAPIClient(account_no_secrets)
        
        self.assertIn("CLARI_API_KEY and CLARI_API_PASSWORD must be configured", str(context.exception))
    
    @patch('core_agent.third_party.clari.requests.get')
    def test_fetch_calls_page_success(self, mock_get):
        """Test successful fetch_calls_page operation."""
        # Mock successful API response
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            'calls': [
                {'id': 'call_1', 'title': 'Test Call 1'},
                {'id': 'call_2', 'title': 'Test Call 2'}
            ]
        }
        mock_get.return_value = mock_response
        
        client = ClariAPIClient(self.mock_account)
        result = client.fetch_calls_page(skip=0)
        
        self.assertEqual(len(result['calls']), 2)
        self.assertEqual(result['calls'][0]['id'], 'call_1')
        mock_get.assert_called_once()
    
    @patch('core_agent.third_party.clari.requests.get')
    def test_fetch_calls_page_api_error(self, mock_get):
        """Test fetch_calls_page with API error."""
        # Mock requests.RequestException which is what the code catches
        from requests.exceptions import RequestException
        mock_get.side_effect = RequestException("API Error")
        
        client = ClariAPIClient(self.mock_account)
        
        with self.assertRaises(ClariAPIError) as context:
            client.fetch_calls_page(skip=0)
        
        self.assertIn("Failed to fetch calls page", str(context.exception))
    
    @patch('core_agent.third_party.clari.requests.get')
    def test_fetch_call_details_success(self, mock_get):
        """Test successful fetch_call_details operation."""
        # Mock successful API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            'call': {
                'transcript': [
                    {'text': 'Hello', 'start': 0, 'end': 1, 'personId': 1}
                ],
                'summary': {'full_summary': 'Call summary'}
            }
        }
        mock_get.return_value = mock_response
        
        client = ClariAPIClient(self.mock_account)
        result = client.fetch_call_details('test_call_id')
        
        self.assertIsNotNone(result)
        self.assertIn('transcript', result)
        self.assertIn('summary', result)
    
    @patch('core_agent.third_party.clari.requests.get')
    def test_fetch_call_details_not_found(self, mock_get):
        """Test fetch_call_details with 404 response."""
        # Mock 404 response
        mock_response = Mock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response
        
        client = ClariAPIClient(self.mock_account)
        result = client.fetch_call_details('non_existent_call')
        
        self.assertIsNone(result)
    
    def test_is_user_allowed(self):
        """Test _is_user_allowed helper method."""
        client = ClariAPIClient(self.mock_account)
        
        # Test call with allowed user
        call_with_allowed_user = {
            'users': [
                {'userEmail': 'allowed@example.com'},
                {'userEmail': 'other@example.com'}
            ]
        }
        allowed_emails = ['allowed@example.com']
        
        self.assertTrue(client._is_user_allowed(call_with_allowed_user, allowed_emails))
        
        # Test call with no allowed users
        call_with_no_allowed_users = {
            'users': [
                {'userEmail': 'notallowed@example.com'}
            ]
        }
        
        self.assertFalse(client._is_user_allowed(call_with_no_allowed_users, allowed_emails))
        
        # Test with empty allowed emails (should allow all)
        self.assertTrue(client._is_user_allowed(call_with_no_allowed_users, []))
    
    def test_enrich_call_data(self):
        """Test _enrich_call_data method."""
        client = ClariAPIClient(self.mock_account)
        
        # Sample call data
        call = {
            'id': 'test_call_id',
            'time': '2023-12-01T10:00:00Z',
            'title': 'Test Call',
            'account_name': 'Test Account',
            'deal_name': 'Test Deal',
            'deal_value': '10000',
            'metrics': {
                'call_duration': 1800,
                'talk_listen_ratio': 0.6,
                'num_questions_asked': 5
            }
        }
        
        details = {
            'transcript': [
                {'text': 'Hello', 'start': 0, 'end': 1, 'personId': 1}
            ],
            'summary': {
                'full_summary': 'Call summary',
                'key_action_items': []
            },
            'users': [
                {'personId': 1, 'userEmail': 'rep@example.com', 'isOrganizer': True}
            ]
        }
        
        enriched = client._enrich_call_data(call, details)
        
        # Verify basic fields
        self.assertEqual(enriched['call_id'], 'test_call_id')
        self.assertEqual(enriched['account_name'], 'Test Account')
        self.assertEqual(enriched['metrics']['duration_seconds'], 1800)
        
        # Verify participants mapping
        self.assertIn(1, enriched['participants'])
        self.assertEqual(enriched['participants'][1]['email'], 'rep@example.com')
        
        # Verify transcript enhancement
        self.assertEqual(enriched['transcript'][0]['speaker_name'], 'Rep')


class TestClariDataAutomationService(unittest.TestCase):
    """Test the Clari data automation service."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_account = Mock()
        self.mock_account.metadata = {
            'secrets': [
                {'key': 'CLARI_API_KEY', 'value': 'test_key'},
                {'key': 'CLARI_API_PASSWORD', 'value': 'test_pass'}
            ]
        }
        
        self.mock_project = Mock()
        self.mock_project.id = 'test_project_id'
        self.mock_project.account = self.mock_account
        self.mock_project.metadata = {'clari_filters': {'max_calls': 10}}
        self.mock_project.blueprints.exists.return_value = False
        self.mock_project.blueprints.all.return_value = []
    
    @patch('core_agent.third_party.clari_data_automation.DataAutomationInvocation')
    @patch('core_agent.third_party.clari_data_automation.create_clari_client')
    def test_execute_clari_data_fetch_success(self, mock_create_client, mock_invocation_class):
        """Test successful execution of Clari data fetch."""
        # Mock invocation creation and saving
        mock_invocation = Mock()
        mock_invocation_class.objects.create.return_value = mock_invocation
        mock_invocation_class.Status.CREATED = 'created'
        mock_invocation_class.Status.IN_PROGRESS = 'in_progress'
        mock_invocation_class.Status.SUCCESS = 'success'
        
        # Mock Clari client
        mock_client = Mock()
        mock_client.fetch_calls_with_details.return_value = [
            {
                'call_id': 'test_call',
                'account_name': 'Test Account',
                'call_date': '2023-12-01',
                'deal_value': '5000'
            }
        ]
        mock_create_client.return_value = mock_client
        
        # Execute the service
        result = ClariDataAutomationService.execute_clari_data_fetch(self.mock_project)
        
        # Verify invocation was created and updated
        mock_invocation_class.objects.create.assert_called_once()
        self.assertEqual(mock_invocation.status, 'success')
        mock_invocation.save.assert_called()
    
    @patch('core_agent.third_party.clari_data_automation.DataAutomationInvocation')
    @patch('core_agent.third_party.clari_data_automation.create_clari_client')
    def test_execute_clari_data_fetch_error(self, mock_create_client, mock_invocation_class):
        """Test error handling in Clari data fetch."""
        # Mock invocation creation
        mock_invocation = Mock()
        mock_invocation_class.objects.create.return_value = mock_invocation
        mock_invocation_class.Status.CREATED = 'created'
        mock_invocation_class.Status.IN_PROGRESS = 'in_progress'
        mock_invocation_class.Status.ERROR = 'error'
        
        # Mock Clari client to raise error
        mock_create_client.side_effect = Exception("API Error")
        
        # Execute the service
        result = ClariDataAutomationService.execute_clari_data_fetch(self.mock_project)
        
        # Verify error was handled
        self.assertEqual(mock_invocation.status, 'error')
        self.assertIn('error_message', mock_invocation.metadata.update.call_args[0][0])
    
    def test_extract_field_value(self):
        """Test field value extraction for Blueprint processing."""
        call_data = {
            'call_id': 'test_call',
            'account_name': 'Test Account',
            'metrics': {
                'duration_seconds': 1800,
                'num_questions_asked': 5
            },
            'participants': {'1': {'name': 'Rep'}, '2': {'name': 'Customer'}}
        }
        
        # Test direct field access
        result = ClariDataAutomationService._extract_field_value(
            call_data, 'call_id', {}
        )
        self.assertEqual(result, 'test_call')
        
        # Test nested field access
        result = ClariDataAutomationService._extract_field_value(
            call_data, 'duration_minutes', {}
        )
        self.assertEqual(result, 1800)  # Should get metrics.duration_seconds
        
        # Test callable mapping
        result = ClariDataAutomationService._extract_field_value(
            call_data, 'participant_count', {}
        )
        self.assertEqual(result, 2)
    
    def test_get_date_range(self):
        """Test date range calculation."""
        call_data = [
            {'call_date': '2023-12-01'},
            {'call_date': '2023-12-05'},
            {'call_date': '2023-12-03'}
        ]
        
        date_range = ClariDataAutomationService._get_date_range(call_data)
        
        self.assertEqual(date_range['start'], '2023-12-01')
        self.assertEqual(date_range['end'], '2023-12-05')
        
        # Test empty data
        empty_range = ClariDataAutomationService._get_date_range([])
        self.assertIsNone(empty_range['start'])
        self.assertIsNone(empty_range['end'])
    
    def test_extract_transcript_text(self):
        """Test transcript text extraction functionality."""
        call_data = {
            'transcript': [
                {
                    'text': 'Hello, this is a test call.',
                    'speaker_name': 'John Doe',
                    'start': 0,
                    'end': 2
                },
                {
                    'text': 'Thank you for calling.',
                    'speaker_name': 'Jane Smith',
                    'start': 2,
                    'end': 4
                },
                {
                    'text': 'How can I help you today?',
                    'speaker_name': 'John Doe',
                    'start': 4,
                    'end': 6
                }
            ]
        }
        
        # Test with speaker names
        transcript_with_speakers = ClariDataAutomationService._extract_transcript_text(
            call_data, include_speakers=True
        )
        expected_with_speakers = (
            "John Doe: Hello, this is a test call.\n"
            "Jane Smith: Thank you for calling.\n"
            "John Doe: How can I help you today?"
        )
        self.assertEqual(transcript_with_speakers, expected_with_speakers)
        
        # Test without speaker names (clean text for chatbot)
        transcript_clean = ClariDataAutomationService._extract_transcript_text(
            call_data, include_speakers=False
        )
        expected_clean = (
            "Hello, this is a test call.\n"
            "Thank you for calling.\n"
            "How can I help you today?"
        )
        self.assertEqual(transcript_clean, expected_clean)
        
        # Test empty transcript
        empty_call_data = {'transcript': []}
        empty_result = ClariDataAutomationService._extract_transcript_text(empty_call_data)
        self.assertEqual(empty_result, "")
        
        # Test call data without transcript
        no_transcript_data = {}
        no_transcript_result = ClariDataAutomationService._extract_transcript_text(no_transcript_data)
        self.assertEqual(no_transcript_result, "")
    
    def test_extract_transcript_field_values(self):
        """Test extraction of transcript-related field values."""
        call_data = {
            'call_id': 'test_call_123',
            'account_name': 'Test Account',
            'transcript': [
                {'text': 'Hello world', 'speaker_name': 'Speaker 1'},
                {'text': 'How are you', 'speaker_name': 'Speaker 2'},
                {'text': 'I am fine', 'speaker_name': 'Speaker 1'}
            ]
        }
        
        # Test transcript_text extraction
        transcript_text = ClariDataAutomationService._extract_field_value(
            call_data, 'transcript_text', {}
        )
        expected_text = (
            "Speaker 1: Hello world\n"
            "Speaker 2: How are you\n"
            "Speaker 1: I am fine"
        )
        self.assertEqual(transcript_text, expected_text)
        
        # Test transcript_clean extraction
        transcript_clean = ClariDataAutomationService._extract_field_value(
            call_data, 'transcript_clean', {}
        )
        expected_clean = (
            "Hello world\n"
            "How are you\n"
            "I am fine"
        )
        self.assertEqual(transcript_clean, expected_clean)
        
        # Test word_count extraction
        word_count = ClariDataAutomationService._extract_field_value(
            call_data, 'word_count', {}
        )
        self.assertEqual(word_count, 8)  # "Hello world How are you I am fine" = 8 words


class TestClariBlueprints(unittest.TestCase):
    """Test Clari blueprint configurations."""
    
    def test_blueprint_schema_validity(self):
        """Test that blueprint schemas are valid JSON Schema."""
        # Test that the schema can be serialized to JSON
        try:
            json.dumps(CLARI_CALL_SUMMARY_BLUEPRINT)
        except (TypeError, ValueError) as e:
            self.fail(f"Blueprint schema is not JSON serializable: {e}")
        
        # Test required structure
        self.assertIn('name', CLARI_CALL_SUMMARY_BLUEPRINT)
        self.assertIn('description', CLARI_CALL_SUMMARY_BLUEPRINT)
        self.assertIn('schema', CLARI_CALL_SUMMARY_BLUEPRINT)
        
        schema = CLARI_CALL_SUMMARY_BLUEPRINT['schema']
        self.assertIn('properties', schema)
        self.assertIn('required', schema)
    
    def test_get_blueprint_by_name(self):
        """Test blueprint retrieval by name."""
        blueprint = get_blueprint_by_name('Clari Call Summary')
        self.assertIsNotNone(blueprint)
        self.assertEqual(blueprint['name'], 'Clari Call Summary')
        
        # Test non-existent blueprint
        missing = get_blueprint_by_name('Non Existent Blueprint')
        self.assertIsNone(missing)
    
    def test_list_available_blueprints(self):
        """Test listing available blueprints."""
        blueprints = list_available_blueprints()
        
        self.assertIsInstance(blueprints, list)
        self.assertGreater(len(blueprints), 0)
        
        # Each blueprint should have name and description
        for blueprint in blueprints:
            self.assertIn('name', blueprint)
            self.assertIn('description', blueprint)
    
    def test_transcript_text_blueprint_schema(self):
        """Test the transcript text blueprint schema."""
        # Test that the schema can be serialized to JSON
        try:
            json.dumps(CLARI_TRANSCRIPT_TEXT_BLUEPRINT)
        except (TypeError, ValueError) as e:
            self.fail(f"Transcript blueprint schema is not JSON serializable: {e}")
        
        # Test required structure
        self.assertIn('name', CLARI_TRANSCRIPT_TEXT_BLUEPRINT)
        self.assertIn('description', CLARI_TRANSCRIPT_TEXT_BLUEPRINT)
        self.assertIn('schema', CLARI_TRANSCRIPT_TEXT_BLUEPRINT)
        
        schema = CLARI_TRANSCRIPT_TEXT_BLUEPRINT['schema']
        self.assertIn('properties', schema)
        self.assertIn('required', schema)
        
        # Test specific transcript fields
        properties = schema['properties']
        self.assertIn('transcript_text', properties)
        self.assertIn('transcript_clean', properties)
        self.assertIn('word_count', properties)
        
        # Test required fields
        required = schema['required']
        self.assertIn('call_id', required)
        self.assertIn('transcript_text', required)
        self.assertIn('transcript_clean', required)
    
    def test_get_transcript_blueprint_by_name(self):
        """Test retrieval of transcript blueprint by name."""
        blueprint = get_blueprint_by_name('Clari Transcript Text')
        self.assertIsNotNone(blueprint)
        self.assertEqual(blueprint['name'], 'Clari Transcript Text')
        self.assertIn('Extract plain text from call transcripts', blueprint['description'])


class TestClariIntegrationEnd2End(unittest.TestCase):
    """End-to-end integration tests for Clari functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_account = Mock()
        self.mock_account.metadata = {
            'secrets': [
                {'key': 'CLARI_API_KEY', 'value': 'test_key'},
                {'key': 'CLARI_API_PASSWORD', 'value': 'test_pass'}
            ]
        }
    
    @patch('core_agent.third_party.clari.requests.get')
    def test_full_data_enrichment_flow(self, mock_get):
        """Test the complete flow from API call to enriched data."""
        # Mock API responses
        calls_response = Mock()
        calls_response.raise_for_status.return_value = None
        calls_response.json.return_value = {
            'calls': [{
                'id': 'test_call_1',
                'time': '2023-12-01T10:00:00Z',
                'title': 'Test Call',
                'account_name': 'Test Account',
                'deal_value': '10000',
                'metrics': {'call_duration': 1800}
            }]
        }
        
        details_response = Mock()
        details_response.status_code = 200
        details_response.raise_for_status.return_value = None
        details_response.json.return_value = {
            'call': {
                'transcript': [
                    {'text': 'Hello world', 'start': 0, 'end': 2, 'personId': 1}
                ],
                'summary': {'full_summary': 'Test summary'},
                'users': [
                    {'personId': 1, 'userEmail': 'rep@example.com', 'isOrganizer': True}
                ]
            }
        }
        
        mock_get.side_effect = [calls_response, details_response]
        
        # Create client and fetch data
        client = ClariAPIClient(self.mock_account)
        enriched_calls = client.fetch_calls_with_details(max_calls=1)
        
        # Verify enriched data structure
        self.assertEqual(len(enriched_calls), 1)
        call = enriched_calls[0]
        
        self.assertEqual(call['call_id'], 'test_call_1')
        self.assertEqual(call['account_name'], 'Test Account')
        self.assertIn('participants', call)
        self.assertIn('transcript', call)
        self.assertIn('summary', call)
        self.assertIn('metrics', call)
        
        # Verify transcript enhancement
        self.assertEqual(call['transcript'][0]['speaker_name'], 'Rep')
        self.assertEqual(call['transcript'][0]['is_internal_speaker'], True)


if __name__ == '__main__':
    unittest.main()