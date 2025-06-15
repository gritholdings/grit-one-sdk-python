import io
from django.test import TestCase
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from core.forms import CSVUploadForm, CSVColumnConfig, parse_csv_data


class CSVUploadTestCase(TestCase):
    """Test cases for the refactored CSV upload functionality"""
    
    def test_csv_upload_form_with_column_config(self):
        """Test that CSVUploadForm correctly displays help text based on column config"""
        config = {
            'columns': ['email', 'name', 'role']
        }
        form = CSVUploadForm(column_config=config)
        self.assertEqual(
            form.fields['csv_file'].help_text,
            "Upload a CSV file with columns: email, name, role"
        )
    
    def test_csv_upload_form_without_config(self):
        """Test that CSVUploadForm works without column config"""
        form = CSVUploadForm()
        self.assertEqual(form.fields['csv_file'].help_text, "Upload a CSV file")
    
    def test_parse_csv_data_with_valid_data(self):
        """Test parsing valid CSV data"""
        csv_content = "email,name,role\ntest@example.com,John Doe,admin\n"
        csv_file = SimpleUploadedFile("test.csv", csv_content.encode('utf-8'))
        
        config = {
            'columns': ['email', 'name', 'role'],
            'validators': {
                'email': lambda x: '@' in x
            }
        }
        
        result = parse_csv_data(csv_file, config)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['email'], 'test@example.com')
        self.assertEqual(result[0]['name'], 'John Doe')
        self.assertEqual(result[0]['role'], 'admin')
        self.assertEqual(result[0]['row_number'], 2)
    
    def test_parse_csv_data_with_normalizers(self):
        """Test parsing CSV data with normalizers"""
        csv_content = "email,role\nTEST@EXAMPLE.COM,student\n"
        csv_file = SimpleUploadedFile("test.csv", csv_content.encode('utf-8'))
        
        config = {
            'columns': ['email', 'role'],
            'normalizers': {
                'email': lambda x: x.lower(),
                'role': lambda x: x.title()
            }
        }
        
        result = parse_csv_data(csv_file, config)
        self.assertEqual(result[0]['email'], 'test@example.com')
        self.assertEqual(result[0]['role'], 'Student')
    
    def test_parse_csv_data_validation_error(self):
        """Test that validation errors are raised correctly"""
        csv_content = "email,role\ninvalid-email,student\n"
        csv_file = SimpleUploadedFile("test.csv", csv_content.encode('utf-8'))
        
        config = {
            'columns': ['email', 'role'],
            'validators': {
                'email': lambda x: '@' in x
            }
        }
        
        with self.assertRaises(ValidationError) as cm:
            parse_csv_data(csv_file, config)
        
        self.assertIn("Row 2", str(cm.exception))
        self.assertIn("Invalid value for 'email'", str(cm.exception))
    
    def test_parse_csv_data_missing_columns(self):
        """Test that missing columns raise ValidationError"""
        csv_content = "email\ntest@example.com\n"
        csv_file = SimpleUploadedFile("test.csv", csv_content.encode('utf-8'))
        
        config = {
            'columns': ['email', 'name', 'role']
        }
        
        with self.assertRaises(ValidationError) as cm:
            parse_csv_data(csv_file, config)
        
        # Check that both missing columns are mentioned in the error
        error_message = str(cm.exception)
        self.assertIn("Missing required columns:", error_message)
        self.assertIn("name", error_message)
        self.assertIn("role", error_message)
    
    def test_csv_column_config_dataclass(self):
        """Test using CSVColumnConfig dataclass"""
        csv_content = "name,email,status\nJohn Doe,john@example.com,active\n"
        csv_file = SimpleUploadedFile("test.csv", csv_content.encode('utf-8'))
        
        config = CSVColumnConfig(
            columns=['name', 'email', 'status'],
            validators={
                'email': lambda x: '@' in x,
                'status': lambda x: x in ['active', 'inactive']
            },
            normalizers={
                'email': lambda x: x.lower()
            }
        )
        
        result = parse_csv_data(csv_file, config)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['email'], 'john@example.com')
        self.assertEqual(result[0]['status'], 'active')
    
    def test_csv_column_config_custom_error_messages(self):
        """Test custom error messages in CSVColumnConfig"""
        csv_content = "email,status\ninvalid-email,unknown\n"
        csv_file = SimpleUploadedFile("test.csv", csv_content.encode('utf-8'))
        
        config = CSVColumnConfig(
            columns=['email', 'status'],
            validators={
                'email': lambda x: '@' in x,
                'status': lambda x: x in ['active', 'inactive']
            },
            custom_error_messages={
                'email': 'Email must contain @ symbol',
                'status': 'Status must be either active or inactive'
            }
        )
        
        with self.assertRaises(ValidationError) as cm:
            parse_csv_data(csv_file, config)
        
        error_message = str(cm.exception)
        self.assertIn('Email must contain @ symbol', error_message)
        self.assertIn('Status must be either active or inactive', error_message)
    
    def test_backward_compatibility_with_dict(self):
        """Test that dict configuration still works"""
        csv_content = "col1,col2\nvalue1,value2\n"
        csv_file = SimpleUploadedFile("test.csv", csv_content.encode('utf-8'))
        
        # Using dict config (backward compatibility)
        dict_config = {
            'columns': ['col1', 'col2'],
            'encoding': 'utf-8'
        }
        
        result = parse_csv_data(csv_file, dict_config)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['col1'], 'value1')
        self.assertEqual(result[0]['col2'], 'value2')
    
    def test_csv_upload_form_with_dataclass(self):
        """Test CSVUploadForm with CSVColumnConfig dataclass"""
        config = CSVColumnConfig(
            columns=['field1', 'field2', 'field3']
        )
        form = CSVUploadForm(column_config=config)
        self.assertEqual(
            form.fields['csv_file'].help_text,
            "Upload a CSV file with columns: field1, field2, field3"
        )