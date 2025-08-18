# Dynamic Model Metadata Registration System

## Overview

The Model Metadata Registration System provides automatic URL generation and view creation for Django models through a decorator-based registration pattern, similar to Django's admin interface.

## Features

- **Auto-Discovery**: Automatically discovers and imports `metadata.py` files from all Django apps
- **Decorator Registration**: Simple `@metadata.register(Model)` decorator for model registration
- **Dynamic URL Generation**: Automatically creates standardized URL patterns for registered models
- **Generic Views**: Auto-generates list, detail, and update views with proper ownership filtering
- **Template Flexibility**: Uses app-specific templates when available, falls back to generic templates

## Quick Start

### 1. Register a Model

Create a `metadata.py` file in your Django app:

```python
from core.metadata import metadata
from myapp.models import MyModel

@metadata.register(MyModel)
class MyModelMetadata(metadata.ModelMetadata):
    list_display = ('name', 'created_at', 'status')
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description')
        }),
        ('Details', {
            'fields': ('status', 'created_at', 'updated_at')
        })
    )
```

### 2. That's It!

The system automatically generates:
- List view: `/m/MyModel/list`
- Detail view: `/r/MyModel/<uuid:mymodel_id>/view`
- Update view: `/r/MyModel/<uuid:mymodel_id>/update`

## URL Pattern Convention

- **List Views**: `m/<ModelName>/list` (e.g., `m/Agent/list`)
- **Detail Views**: `r/<ModelName>/<uuid:modelname_id>/view` (e.g., `r/Agent/<uuid:agent_id>/view`)
- **Update Views**: `r/<ModelName>/<uuid:modelname_id>/update` (e.g., `r/Agent/<uuid:agent_id>/update`)

Where:
- `m/` prefix = "model" (list views)
- `r/` prefix = "record" (detail/update views)
- Model names preserve their case (e.g., "Agent" not "agent")

## Metadata Configuration

### ModelMetadata Class

The `ModelMetadata` base class supports the following attributes:

```python
class MyModelMetadata(metadata.ModelMetadata):
    # Fields to display in list view
    list_display = ('field1', 'field2', 'field3')
    
    # Field grouping for detail views
    fieldsets = (
        ('Section Name', {
            'fields': ('field1', 'field2')
        }),
        ('Another Section', {
            'fields': ('field3', 'field4')
        })
    )
```

## View Generation

### Ownership Filtering

The generated views automatically handle ownership filtering:

1. If the model has an `owned` manager, it uses that for filtering
2. If the model has an `owner` field, it filters by `owner=request.user`
3. Otherwise, no ownership filtering is applied

### Template Resolution

Views look for templates in the following order:

#### List View Templates:
1. `{app_label}/{model_name_lower}_listview.html`
2. `core/base_list_view.html`
3. `core/generic_list_view.html`
4. Falls back to JSON response if no template found

#### Detail View Templates:
1. `{app_label}/{model_name_lower}_detail.html`
2. `core/base_detail_view.html`
3. `core/generic_detail_view.html`
4. Falls back to JSON response if no template found

## Data Format

### List View Context

```python
{
    'items': json_serialized_list,  # List of model instances
    'model_name': 'ModelName',      # e.g., 'Agent'
    'model_name_lower': 'modelname', # e.g., 'agent'
    'title': 'ModelName List'       # Page title
}
```

### Detail View Context

```python
{
    'object': model_instance,        # The model instance
    'object_data': json_serialized,  # JSON serialized instance data
    'fieldsets': json_fieldsets,     # Fieldsets configuration
    'model_name': 'ModelName',       # e.g., 'Agent'
    'model_name_lower': 'modelname', # e.g., 'agent'
    'title': 'ModelName Detail'      # Page title
}
```

## React Integration

The system is designed to work with React components. Data is passed via data attributes:

```html
<div data-react-component="ListView" 
     data-items="{{ items }}" 
     data-model-name="{{ model_name }}">
</div>
```

## Form Integration

Update views automatically look for a form class named `{ModelName}Form` in the app's `forms.py`:

```python
# myapp/forms.py
from django import forms
from core.admin.metadata import MetadataMixin
from .models import MyModel

class MyModelForm(MetadataMixin, forms.ModelForm):
    metadata_fields = ('field_in_metadata_json',)
    
    class Meta:
        model = MyModel
        fields = ['name', 'description']
```

## Advanced Usage

### Custom View Logic

To override the auto-generated views while keeping the URL patterns:

```python
# In your app's views.py
from core.metadata.views import MetadataViewGenerator

class CustomViewGenerator(MetadataViewGenerator):
    @staticmethod
    def create_list_view(model, metadata_class):
        # Your custom list view logic
        pass
```

### Excluding Models

To temporarily exclude a model from auto-generation, simply comment out or remove the registration:

```python
# @metadata.register(MyModel)  # Commented out to disable
```

### Manual URL Override

Manual URLs defined in `app/urls.py` take precedence over auto-generated ones if they appear earlier in the URL configuration.

## Migration Guide

### From Manual URLs to Metadata System

1. **Before** (in `app/urls.py`):
```python
path('m/Agent/list', views.agent_listview, name='agent_listview'),
path('r/Agent/<uuid:agent_id>/view', views.agent_detail, name='agent_detailview'),
```

2. **After** (in `chatbot_app/metadata.py`):
```python
@metadata.register(Agent)
class AgentMetadata(metadata.ModelMetadata):
    list_display = ('name', 'status')
    fieldsets = (...)
```

3. **Remove** the manual URL patterns from `urls.py`

## Debugging

### Check Registered Models

```python
python manage.py shell
>>> from core.metadata import metadata
>>> metadata.get_registered_models()
```

### View All Generated URLs

```bash
python manage.py show_urls --filter modelname
```

### Verify Auto-Discovery

```python
python manage.py shell
>>> from core.metadata.autodiscover import autodiscover
>>> autodiscover()  # Should import all metadata.py files
```

## Requirements

- Django 3.2+
- Models must use UUID primary keys
- User model must have an `id` field for ownership filtering

## Troubleshooting

### URLs Not Appearing
- Ensure `metadata.py` exists in your app directory
- Check that the model is properly registered with `@metadata.register(Model)`
- Verify auto-discovery is called in `core/urls.py`

### Template Not Found
- Create app-specific templates in `{app}/templates/{app}/{model}_listview.html`
- Or rely on the generic templates in `core/templates/core/`

### Ownership Filtering Issues
- Ensure your model has either an `owned` manager or an `owner` field
- Check that the user is authenticated before accessing views

## Example: Agent Model

```python
# chatbot_app/metadata.py
from core.metadata import metadata
from core_agent.models import Agent

@metadata.register(Agent)
class AgentMetadata(metadata.ModelMetadata):
    list_display = ('name', 'model_name')
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description')
        }),
        ('Configuration', {
            'fields': ('model_name', 'temperature', 'max_tokens')
        })
    )
```

This automatically creates:
- `/m/Agent/list` - List all agents owned by the user
- `/r/Agent/<uuid>/view` - View agent details
- `/r/Agent/<uuid>/update` - Update agent via AJAX