import os
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()

import json
import unittest
from unittest.mock import patch, Mock
from core_agent.store import MemoryStoreService


class TestOpenAIAgentDatetimeSerialization(unittest.TestCase):
    """Test that datetime objects are properly serialized to prevent JSON errors."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.service = MemoryStoreService()
        self.created_memories = []  # Track memories created during tests
    
    def tearDown(self):
        """Clean up test fixtures and memory records."""
        # Clean up all memories created during tests
        for namespace, thread_id in self.created_memories:
            try:
                self.service.delete_memory(namespace, thread_id)
            except Exception:
                pass  # Ignore if already deleted or doesn't exist
        
        self.service.close()
    
    @patch.object(MemoryStoreService, 'get_store')
    @patch.object(MemoryStoreService, 'get_memory')
    @patch.object(MemoryStoreService, 'put_memory')
    def test_upsert_memory_datetime_json_serializable(self, mock_put_memory, mock_get_memory, mock_get_store):
        """Test that upsert_memory creates JSON-serializable data with datetime fields."""
        namespace = ("test", "datetime", "serialization")
        thread_id = "datetime_test_thread"
        key = "test_key"
        memory = "test_memory_content"
        
        # Mock that no memory exists initially
        mock_get_memory.side_effect = [
            None,  # First call - no thread exists
            Mock(value={"created_at": "2023-01-01T12:00:00.000000", "updated_at": "2023-01-01T12:00:00.000000"})  # Second call
        ]
        
        # Call upsert_memory
        self.service.upsert_memory(namespace, thread_id, key, memory)
        
        # Get the data that was passed to put_memory
        put_memory_calls = mock_put_memory.call_args_list
        self.assertEqual(len(put_memory_calls), 2)  # Should be called twice
        
        # Check both calls contain JSON-serializable data
        for call in put_memory_calls:
            call_args = call[0]  # Get positional arguments
            memory_data = call_args[2]  # Third argument is the memory data
            
            # Test that the memory data can be JSON serialized without errors
            try:
                json_string = json.dumps(memory_data)
                # Also test that it can be deserialized
                deserialized_data = json.loads(json_string)
                
                # Verify datetime fields are strings in ISO format
                if 'created_at' in memory_data:
                    self.assertIsInstance(memory_data['created_at'], str)
                    # Verify it's a valid ISO format datetime string
                    from datetime import datetime
                    datetime.fromisoformat(memory_data['created_at'])
                
                if 'updated_at' in memory_data:
                    self.assertIsInstance(memory_data['updated_at'], str)
                    # Verify it's a valid ISO format datetime string
                    datetime.fromisoformat(memory_data['updated_at'])
                    
            except (TypeError, ValueError) as e:
                self.fail(f"Memory data is not JSON serializable: {e}. Data: {memory_data}")
    
    @patch.object(MemoryStoreService, 'get_store')
    @patch.object(MemoryStoreService, 'get_memory')
    @patch.object(MemoryStoreService, 'put_memory')
    def test_upsert_memory_existing_data_preserves_json_serializability(self, mock_put_memory, mock_get_memory, mock_get_store):
        """Test that upsert_memory preserves JSON serializability when updating existing data."""
        namespace = ("test", "existing", "serialization")
        thread_id = "existing_test_thread"
        key = "existing_key"
        memory = "new_memory_content"
        
        # Mock existing memory with ISO format datetime strings
        existing_memory = Mock(value={
            "existing_key": ["old_memory"],
            "created_at": "2023-01-01T10:00:00.000000",
            "updated_at": "2023-01-01T10:00:00.000000"
        })
        mock_get_memory.return_value = existing_memory
        
        # Call upsert_memory
        self.service.upsert_memory(namespace, thread_id, key, memory)
        
        # Get the final data that was passed to put_memory
        final_call = mock_put_memory.call_args_list[-1]
        final_memory_data = final_call[0][2]  # Third argument is the memory data
        
        # Test that the final memory data is JSON serializable
        try:
            json_string = json.dumps(final_memory_data)
            deserialized_data = json.loads(json_string)
            
            # Verify structure is preserved
            self.assertIn("existing_key", final_memory_data)
            self.assertIn("created_at", final_memory_data)
            self.assertIn("updated_at", final_memory_data)
            
            # Verify datetime fields are strings
            self.assertIsInstance(final_memory_data['created_at'], str)
            self.assertIsInstance(final_memory_data['updated_at'], str)
            
            # Verify memory was appended correctly
            self.assertEqual(final_memory_data["existing_key"], ["old_memory", "new_memory_content"])
            
        except (TypeError, ValueError) as e:
            self.fail(f"Updated memory data is not JSON serializable: {e}. Data: {final_memory_data}")
    
    def test_datetime_isoformat_produces_json_serializable_string(self):
        """Test that datetime.now().isoformat() produces JSON-serializable strings."""
        from datetime import datetime
        
        # Test current implementation
        now_iso = datetime.now().isoformat()
        
        # Verify it's a string
        self.assertIsInstance(now_iso, str)
        
        # Verify it's JSON serializable
        try:
            json_string = json.dumps({"timestamp": now_iso})
            deserialized = json.loads(json_string)
            self.assertEqual(deserialized["timestamp"], now_iso)
        except (TypeError, ValueError) as e:
            self.fail(f"ISO format datetime string is not JSON serializable: {e}")
        
        # Verify it can be parsed back to datetime
        try:
            parsed_datetime = datetime.fromisoformat(now_iso)
            self.assertIsInstance(parsed_datetime, datetime)
        except ValueError as e:
            self.fail(f"ISO format string cannot be parsed back to datetime: {e}")


class TestModelLookupError(unittest.TestCase):
    """Test model class lookup error handling."""
    
    def test_agent_get_agent_class_with_invalid_string(self):
        """Test get_agent_class with invalid agent class string."""
        from core_agent.models import Agent
        
        # Test with invalid agent class string
        invalid_class_str = "nonexistent.module.NonExistentClass"
        
        with self.assertRaises((ImportError, AttributeError)):
            Agent.objects.get_agent_class(agent_class_str=invalid_class_str)
    
    def test_agent_get_agent_class_with_empty_string(self):
        """Test get_agent_class with empty string returns None."""
        from core_agent.models import Agent
        
        result = Agent.objects.get_agent_class(agent_class_str="")
        self.assertIsNone(result)
        
        result = Agent.objects.get_agent_class(agent_class_str=None)
        self.assertIsNone(result)
    
    def test_course_lookup_with_non_existent_uuid(self):
        """Test Course lookup with non-existent UUID raises ObjectDoesNotExist."""
        from django.core.exceptions import ObjectDoesNotExist
        
        # Import Course model if available
        try:
            from core_classroom.models import Course
            
            # Test with a UUID that doesn't exist
            non_existent_uuid = "28105bb0-d1a3-4d53-aec4-ee841024872f"
            
            # This should raise ObjectDoesNotExist
            with self.assertRaises(ObjectDoesNotExist):
                Course.objects.select_related('agent').get(id=non_existent_uuid)
                
        except ImportError:
            # Skip test if Course model is not available
            self.skipTest("Course model not available")
    
    def test_safe_agent_lookup_with_uuid(self):
        """Test safe Agent lookup that returns None instead of raising exception."""
        from core_agent.models import Agent
        
        # Test with a UUID that doesn't exist
        non_existent_uuid = "28105bb0-d1a3-4d53-aec4-ee841024872f"
        
        # Safe lookup should return None
        try:
            result = Agent.objects.filter(id=non_existent_uuid).first()
            self.assertIsNone(result)
        except Exception as e:
            self.fail(f"Safe lookup should not raise exception: {e}")


if __name__ == '__main__':
    unittest.main()