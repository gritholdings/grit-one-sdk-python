"""
Example usage of the CSVColumnConfig interface for CSV upload functionality.
"""

from core.forms import CSVColumnConfig, CSVUploadForm, parse_csv_data

# Example 1: Basic configuration
basic_config = CSVColumnConfig(
    columns=['email', 'name', 'department']
)

# Example 2: Configuration with validators
validated_config = CSVColumnConfig(
    columns=['email', 'name', 'age', 'status'],
    validators={
        'email': lambda x: '@' in x and '.' in x.split('@')[1],
        'age': lambda x: x.isdigit() and 18 <= int(x) <= 100,
        'status': lambda x: x.lower() in ['active', 'inactive', 'pending']
    }
)

# Example 3: Configuration with normalizers
normalized_config = CSVColumnConfig(
    columns=['email', 'name', 'country'],
    normalizers={
        'email': lambda x: x.lower().strip(),
        'name': lambda x: x.title().strip(),
        'country': lambda x: x.upper()
    }
)

# Example 4: Full configuration with custom error messages
full_config = CSVColumnConfig(
    columns=['product_id', 'product_name', 'price', 'category'],
    validators={
        'product_id': lambda x: x.isdigit() and len(x) == 6,
        'price': lambda x: x.replace('.', '').isdigit() and float(x) > 0,
        'category': lambda x: x in ['electronics', 'clothing', 'food', 'books']
    },
    normalizers={
        'product_name': lambda x: x.strip().title(),
        'category': lambda x: x.lower()
    },
    custom_error_messages={
        'product_id': 'Product ID must be a 6-digit number',
        'price': 'Price must be a positive number',
        'category': 'Category must be one of: electronics, clothing, food, books'
    },
    encoding='utf-8'  # Default is 'utf-8'
)

# Example 5: Using the configuration with forms and parsing
def process_csv_upload(request):
    config = CSVColumnConfig(
        columns=['user_email', 'first_name', 'last_name', 'role'],
        validators={
            'user_email': lambda email: '@' in email,
            'role': lambda role: role in ['admin', 'user', 'guest']
        },
        normalizers={
            'user_email': lambda email: email.lower(),
            'first_name': lambda name: name.capitalize(),
            'last_name': lambda name: name.capitalize()
        },
        custom_error_messages={
            'user_email': 'Please provide a valid email address',
            'role': 'Role must be either admin, user, or guest'
        }
    )
    
    if request.method == 'POST':
        form = CSVUploadForm(request.POST, request.FILES, column_config=config)
        if form.is_valid():
            try:
                data = parse_csv_data(form.cleaned_data['csv_file'], config)
                # Process the data...
                for row in data:
                    print(f"Processing user: {row['user_email']} with role {row['role']}")
            except ValidationError as e:
                # Handle validation errors
                print(f"CSV validation failed: {e}")
    else:
        form = CSVUploadForm(column_config=config)
    
    return form

# Example 6: Backward compatibility - still works with dictionaries
legacy_config = {
    'columns': ['id', 'name', 'value'],
    'validators': {
        'id': lambda x: x.isdigit()
    },
    'encoding': 'utf-8'
}
# This dictionary config will be automatically converted to CSVColumnConfig