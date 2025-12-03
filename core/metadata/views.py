"""
Generic view generators for metadata-registered models.
"""

import json
from django import forms
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse, Http404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.core.serializers.json import DjangoJSONEncoder
from app import settings
from core.utils.case_conversion import convert_keys_to_camel_case, resolve_urls_in_app_metadata, camel_to_snake
from core.utils.permissions import (
    filter_app_metadata_by_user_groups,
    filter_app_metadata_by_user_profile,
    merge_filtered_settings,
    check_profile_permission,
    check_group_permission,
    get_user_field_permissions,
    check_field_readable,
    check_field_editable
)


def _is_field_readable(
    field_name: str,
    field_perms: dict,
    has_field_config: bool,
    view_all_fields: bool
) -> bool:
    """
    Check if a field is readable based on permission configuration.

    This helper centralizes the field readability logic to ensure consistent
    behavior across all views. It handles the interaction between view_all_fields
    and field_permissions correctly.

    Args:
        field_name: The name of the field to check
        field_perms: Dictionary of explicit field permissions from get_user_field_permissions()
        has_field_config: Whether the profile has any field_permissions configured
        view_all_fields: Whether view_all_fields is enabled for this model

    Returns:
        True if the field is readable, False otherwise

    Logic:
        1. If field is explicitly configured in field_perms, use that setting
        2. If view_all_fields is True and field not explicitly denied, allow read
        3. If has_field_config but field not in whitelist, deny (whitelist mode)
        4. Otherwise allow (no restrictions - superuser or no config)
    """
    # Case 1: Field has explicit permission configuration
    if field_name in field_perms:
        return field_perms[field_name].get('readable', True)

    # Case 2: view_all_fields grants read access to unlisted fields
    if view_all_fields:
        return True

    # Case 3: Whitelist mode - field not in whitelist means deny
    if has_field_config:
        return False

    # Case 4: No restrictions (superuser, no profile, or no field config)
    return True


def _get_user_queryset(model, user):
    """
    Get queryset filtered by user permissions using available manager.

    This helper method checks for managers in priority order and applies
    appropriate user-based filtering. It supports both the standardized
    'scoped' manager and legacy 'owned' manager for backward compatibility.

    Priority order:
    1. 'scoped' manager with for_user() method (standardized, supports superuser bypass)
    2. 'owned' manager with for_user() method (legacy)
    3. 'owned' manager with direct filter
    4. 'objects' manager with owner field filter
    5. 'objects' manager returning all records (no filtering)

    Args:
        model: The Django model class
        user: The user object (or user ID) for filtering

    Returns:
        QuerySet filtered appropriately for the user

    Examples:
        >>> queryset = _get_user_queryset(Account, request.user)
        >>> # Returns Account.scoped.for_user(request.user) if available
    """
    # Priority 1: Check for standardized 'scoped' manager
    if hasattr(model, 'scoped') and hasattr(model.scoped, 'for_user'):
        return model.scoped.for_user(user)

    # Priority 2-3: Check for legacy 'owned' manager
    if hasattr(model, 'owned'):
        if hasattr(model.owned, 'for_user'):
            # Use for_user method if available (e.g., Agent, CourseWork)
            return model.owned.for_user(user.id if hasattr(user, 'id') else user)
        else:
            # Fallback to direct filter
            return model.owned.filter(owner=user)

    # Priority 4-5: Fallback to default 'objects' manager
    if hasattr(model, 'objects'):
        # Try to filter by owner if the field exists
        if hasattr(model, 'owner'):
            return model.objects.filter(owner=user)
        else:
            # No ownership concept - return all
            return model.objects.all()

    # Edge case: no manager found (should rarely happen)
    # Return empty queryset instead of empty list to maintain API consistency
    if hasattr(model, 'objects'):
        return model.objects.none()

    # Absolute edge case - create a manager on the fly
    from django.db import models as django_models
    return django_models.Manager().none()


def serialize_form_for_react(form_class, user=None, instance=None, model_name=None):
    """
    Serialize a Django form class into React component format.

    Args:
        form_class: The form class to serialize
        user: Optional user for context-aware filtering and field permissions
        instance: Optional instance for editing forms
        model_name: Optional model name (lowercase) for field permission checks

    Returns dict mapping field names to FieldConfig objects with:
    - widget: "TextInput" | "Textarea" | "Select"
    - help_text: optional help text
    - required: boolean
    - choices: for Select widgets
    - disabled: boolean (True if field is not editable per field permissions)

    Fields with readable=False are excluded entirely from the result.
    """
    if not form_class:
        return {}

    try:
        # Build form kwargs with optional user and instance
        form_kwargs = {}
        if instance:
            form_kwargs['instance'] = instance
        if user:
            form_kwargs['user'] = user

        form_instance = form_class(**form_kwargs)
    except Exception:
        # If form can't be instantiated with these arguments, try without them
        try:
            form_instance = form_class()
        except Exception:
            # If form still can't be instantiated, return empty
            return {}

    # Get field permissions if user and model_name provided
    field_perms = {}
    has_field_config = False
    view_all_fields = False
    if user and model_name:
        field_perms, has_field_config, view_all_fields = get_user_field_permissions(user, model_name, settings.APP_METADATA_SETTINGS)

    form_data = {}

    for field_name, field in form_instance.fields.items():
        # Check field permissions - skip non-readable fields
        if not _is_field_readable(field_name, field_perms, has_field_config, view_all_fields):
            continue

        # Map Django widgets to React component types
        widget_type = "TextInput"  # default

        # Check the widget type
        widget = field.widget
        if isinstance(widget, forms.Textarea):
            widget_type = "Textarea"
        elif isinstance(widget, (forms.Select, forms.RadioSelect, forms.CheckboxSelectMultiple)):
            widget_type = "Select"
        elif isinstance(widget, forms.CheckboxInput):
            widget_type = "Checkbox"
        elif isinstance(widget, (forms.DateInput, forms.DateTimeInput)):
            widget_type = "DateInput"
        elif isinstance(widget, forms.NumberInput):
            widget_type = "NumberInput"
        elif isinstance(widget, forms.EmailInput):
            widget_type = "EmailInput"

        field_config = {
            "widget": widget_type,
            "required": field.required,
        }

        # Check if field is editable - add disabled flag if not
        if has_field_config or view_all_fields:
            # Check if field has explicit permissions
            if field_name in field_perms:
                # Field is explicitly configured, check if editable
                if not field_perms[field_name].get('editable', True):
                    # Field is readable but not editable - mark as disabled
                    field_config["disabled"] = True
            elif view_all_fields:
                # Field is readable via view_all_fields but has no explicit edit permission
                # view_all_fields only grants read access, not edit - mark as disabled
                field_config["disabled"] = True
            elif has_field_config:
                # Whitelist mode: field not in whitelist means no edit permission
                field_config["disabled"] = True

        # Add help text if present
        if field.help_text:
            field_config["help_text"] = str(field.help_text)

        # Add choices for choice fields
        if hasattr(field, 'choices') and field.choices:
            field_config["choices"] = [
                {"value": str(choice[0]), "label": str(choice[1])}
                for choice in field.choices
                if choice[0] != ''  # Skip empty choice
            ]

        # Add other useful field attributes
        if hasattr(field, 'max_length') and field.max_length:
            field_config["max_length"] = field.max_length

        if hasattr(field, 'min_length') and field.min_length:
            field_config["min_length"] = field.min_length

        # Add label if different from field name
        if field.label and field.label != field_name.replace('_', ' ').title():
            field_config["label"] = str(field.label)

        form_data[field_name] = field_config

    return form_data


class MetadataViewGenerator:
    """
    Factory class for generating generic views based on model metadata.
    """
    
    @staticmethod
    def create_list_view(model, metadata_class):
        """
        Create a generic list view for a model.
        
        Args:
            model: The Django model class
            metadata_class: The metadata configuration class
            
        Returns:
            A view function for listing model instances
        """
        @login_required
        def list_view(request):
            # Check view permission using OR logic across three permission layers
            # Superusers bypass permission checks
            app_label = model._meta.app_label
            model_name = model.__name__
            model_name_lower = camel_to_snake(model_name)
            permission = f'{app_label}.view_{model_name_lower}'

            # Skip permission checks for superusers
            if not request.user.is_superuser:
                # Check all three permission layers (OR logic)
                django_granted = request.user.has_perm(permission)
                groups_granted = check_group_permission(request.user, model_name_lower, settings.APP_METADATA_SETTINGS)
                profiles_granted = check_profile_permission(request.user, model_name_lower, 'allow_read', settings.APP_METADATA_SETTINGS)

                # Use OR logic: if ANY permission check passes, grant access
                if not (django_granted or groups_granted or profiles_granted):
                    # All three checks failed - deny access
                    raise Http404()

            # Get the model name (already defined above)
            # Get user-specific queryset using helper method
            queryset = _get_user_queryset(model, request.user)

            # Apply ordering from metadata if specified
            if hasattr(metadata_class, 'ordering') and metadata_class.ordering:
                queryset = queryset.order_by(*metadata_class.ordering)

            # Get field permissions for filtering
            field_perms, has_field_config, view_all_fields = get_user_field_permissions(request.user, model_name_lower, settings.APP_METADATA_SETTINGS)

            # Prepare data for the template
            items_data = []
            for item in queryset:
                item_dict = {
                    'id': str(item.id),
                    'name': getattr(item, 'name', str(item)),
                }

                # Add fields from list_display if specified
                if hasattr(metadata_class, 'list_display'):
                    for field_name in metadata_class.list_display:
                        # Check field permission - skip non-readable fields
                        if not _is_field_readable(field_name, field_perms, has_field_config, view_all_fields):
                            continue

                        if hasattr(item, field_name):
                            # Check if it's a property first
                            attr = getattr(type(item), field_name, None)
                            if isinstance(attr, property):
                                # It's a property, get its value directly
                                item_dict[field_name] = getattr(item, field_name)
                            else:
                                value = getattr(item, field_name)
                                # Handle special field types
                                if hasattr(value, 'id'):  # Foreign key
                                    item_dict[field_name] = str(value)
                                elif callable(value):  # Method
                                    item_dict[field_name] = value()
                                else:
                                    item_dict[field_name] = value
                        elif hasattr(item, 'metadata') and item.metadata and field_name in item.metadata:
                            # Field is in metadata JSONField
                            item_dict[field_name] = item.metadata.get(field_name, '')

                # Add metadata fields if present
                if hasattr(item, 'metadata') and item.metadata:
                    # Check if metadata is a dict
                    if isinstance(item.metadata, dict):
                        for key, value in item.metadata.items():
                            if key not in item_dict:  # Don't override actual fields
                                # Check field permission before adding
                                if not _is_field_readable(key, field_perms, has_field_config, view_all_fields):
                                    continue
                                item_dict[key] = value

                items_data.append(item_dict)

            # Generate columns configuration from list_display
            columns = []

            # Always add a select column first
            columns.append({'type': 'select'})

            # Generate columns from list_display if available
            if hasattr(metadata_class, 'list_display') and metadata_class.list_display:
                first_column_added = False
                for field_name in metadata_class.list_display:
                    # Check field permission - skip non-readable fields
                    if not _is_field_readable(field_name, field_perms, has_field_config, view_all_fields):
                        continue

                    # Make the first readable field a link to the detail view
                    if not first_column_added:
                        columns.append({
                            'type': 'link',
                            'fieldName': field_name,
                            'label': field_name.replace('_', ' ').title(),
                            'href': f'/r/{model_name_lower}/{{id}}/view',
                            'linkText': f'{{{field_name}}}',
                            'sortable': True
                        })
                        first_column_added = True
                    else:
                        # Regular text columns don't need 'type' field
                        columns.append({
                            'fieldName': field_name,
                            'label': field_name.replace('_', ' ').title(),
                            'sortable': True
                        })
            else:
                # Default columns if no list_display specified
                columns.append({
                    'type': 'link',
                    'fieldName': 'name',
                    'label': 'Name',
                    'href': f'/r/{model_name_lower}/{{id}}/view',
                    'linkText': '{name}',
                    'sortable': True
                })
            
            # Check for list_actions in metadata class
            actions = []
            if hasattr(metadata_class, 'list_actions'):
                actions = metadata_class.list_actions
            
            # Process actions to handle standardized "new" action
            processed_actions = []
            has_new_action = False
            
            if actions and isinstance(actions, list):
                # Check if it's already grouped (list of lists)
                if actions and isinstance(actions[0], list):
                    # It's grouped - process each group
                    for group in actions:
                        processed_group = []
                        for action in group:
                            if isinstance(action, dict):
                                # Check for standardized "new" action
                                if action.get('action') == 'new' or action.get('name') == 'new':
                                    # Replace with standardized create action
                                    has_new_action = True
                                    processed_group.append({
                                        'label': action.get('label', f'New {model_name}'),
                                        'action': 'create',
                                        'url': f'/m/{model_name_lower}/create',
                                        'method': 'GET'
                                    })
                                elif action.get('action') != 'create':  # Skip any existing create actions
                                    processed_group.append(action)
                            else:
                                # Handle string actions
                                if action == 'new':
                                    has_new_action = True
                                    processed_group.append({
                                        'label': f'New {model_name}',
                                        'action': 'create',
                                        'url': f'/m/{model_name_lower}/create',
                                        'method': 'GET'
                                    })
                                else:
                                    processed_group.append(action)
                        if processed_group:
                            processed_actions.append(processed_group)
                else:
                    # It's a flat list - process it
                    processed_group = []
                    for action in actions:
                        if isinstance(action, dict):
                            # Check for standardized "new" action
                            if action.get('action') == 'new' or action.get('name') == 'new':
                                has_new_action = True
                                processed_group.append({
                                    'label': action.get('label', f'New {model_name}'),
                                    'action': 'create',
                                    'url': f'/m/{model_name_lower}/create',
                                    'method': 'GET'
                                })
                            elif action.get('action') != 'create':  # Skip any existing create actions
                                processed_group.append(action)
                        else:
                            # Handle string actions
                            if action == 'new':
                                has_new_action = True
                                processed_group.append({
                                    'label': f'New {model_name}',
                                    'action': 'create',
                                    'url': f'/m/{model_name_lower}/create',
                                    'method': 'GET'
                                })
                            else:
                                processed_group.append(action)
                    if processed_group:
                        processed_actions = [processed_group]
            
            # Use processed actions or empty list if no actions
            actions = processed_actions if processed_actions else [[]]
            
            # Filter app metadata based on user's group and profile permissions (OR logic)
            group_filtered = filter_app_metadata_by_user_groups(settings.APP_METADATA_SETTINGS, request.user)
            profile_filtered = filter_app_metadata_by_user_profile(settings.APP_METADATA_SETTINGS, request.user)
            filtered_settings = merge_filtered_settings(group_filtered, profile_filtered, settings.APP_METADATA_SETTINGS)

            context = {
                'items': items_data,  # Pass raw data, template will JSON encode it
                'columns': json.dumps(columns, cls=DjangoJSONEncoder),
                'actions': json.dumps(actions, cls=DjangoJSONEncoder),
                'model_name': model_name,
                'model_name_lower': model_name_lower,
                'title': f'{model_name} List',
                'app_metadata_settings_json': json.dumps(convert_keys_to_camel_case(resolve_urls_in_app_metadata(filtered_settings)))
            }
            
            # Try to use app-specific template, fall back to generic
            template_names = [
                f'{model._meta.app_label}/{model_name_lower}_listview.html',
                'core/base_list_view.html',
                'core/generic_list_view.html'
            ]
            
            # Use the first available template
            from django.template import TemplateDoesNotExist
            last_error = None
            for template_name in template_names:
                try:
                    return render(request, template_name, context)
                except TemplateDoesNotExist:
                    continue
                except Exception as e:
                    # Store the error but continue trying other templates
                    last_error = e
                    continue
            
            # If we had a rendering error (not just missing templates), raise it
            if last_error:
                raise last_error

            # If no template found, raise an error
            raise TemplateDoesNotExist(
                f"No template found for {model_name_lower} list view. Tried: {', '.join(template_names)}"
            )
        
        # Set a meaningful name for the view function
        list_view.__name__ = f'{model.__name__.lower()}_listview'
        return list_view
    
    @staticmethod
    def create_detail_view(model, metadata_class):
        """
        Create a generic detail view for a model.
        
        Args:
            model: The Django model class
            metadata_class: The metadata configuration class
            
        Returns:
            A view function for displaying model instance details
        """
        @login_required
        def detail_view(request, **kwargs):
            # Get the model name and ID parameter
            model_name = model.__name__
            model_name_lower = camel_to_snake(model_name)
            id_param = f'{model_name_lower}_id'
            app_label = model._meta.app_label
            permission = f'{app_label}.view_{model_name_lower}'

            # Check view permission using OR logic across three permission layers
            # Superusers bypass permission checks
            if not request.user.is_superuser:
                # Check all three permission layers (OR logic)
                django_granted = request.user.has_perm(permission)
                groups_granted = check_group_permission(request.user, model_name_lower, settings.APP_METADATA_SETTINGS)
                profiles_granted = check_profile_permission(request.user, model_name_lower, 'allow_read', settings.APP_METADATA_SETTINGS)

                # Use OR logic: if ANY permission check passes, grant access
                if not (django_granted or groups_granted or profiles_granted):
                    # All three checks failed - deny access
                    raise Http404()

            # Get the object ID from kwargs
            object_id = kwargs.get(id_param)
            if not object_id:
                raise Http404(f"No {model_name} ID provided")
            
            # Get the object with ownership check using helper method
            queryset = _get_user_queryset(model, request.user)
            obj = get_object_or_404(queryset, id=object_id)

            # Get field permissions for filtering
            field_perms, has_field_config, view_all_fields = get_user_field_permissions(request.user, model_name_lower, settings.APP_METADATA_SETTINGS)

            # Prepare data for the template
            obj_data = {
                'id': str(obj.id),
                'name': getattr(obj, 'name', str(obj)),
            }

            # Add all model fields
            for field in model._meta.fields:
                field_name = field.name

                # Check field permission - skip non-readable fields
                if not _is_field_readable(field_name, field_perms, has_field_config, view_all_fields):
                    continue

                value = getattr(obj, field_name)

                # Handle different field types
                if value is None:
                    obj_data[field_name] = None
                elif hasattr(value, 'id'):  # Foreign key
                    obj_data[field_name] = {
                        'id': str(value.id),
                        'name': getattr(value, 'name', str(value))
                    }
                elif field.get_internal_type() == 'UUIDField':
                    obj_data[field_name] = str(value)
                elif field.get_internal_type() == 'DateTimeField':
                    obj_data[field_name] = value.isoformat() if value else None
                elif field.get_internal_type() == 'JSONField':
                    obj_data[field_name] = value or {}
                else:
                    obj_data[field_name] = value

            # Add many-to-many fields
            for field in model._meta.many_to_many:
                field_name = field.name

                # Check field permission - skip non-readable fields
                if not _is_field_readable(field_name, field_perms, has_field_config, view_all_fields):
                    continue

                related_objects = getattr(obj, field_name).all()
                obj_data[field_name] = [
                    {'id': str(item.id), 'name': getattr(item, 'name', str(item))}
                    for item in related_objects
                ]

            # Add metadata fields if present
            if hasattr(obj, 'metadata') and obj.metadata:
                obj_data['metadata'] = obj.metadata

            # Process fieldset fields to ensure all configured fields are included
            if hasattr(metadata_class, 'fieldsets') and metadata_class.fieldsets:
                for fieldset_name, fieldset_config in metadata_class.fieldsets:
                    field_names = fieldset_config.get('fields', [])

                    for field_name in field_names:
                        # Check field permission - skip non-readable fields
                        if not _is_field_readable(field_name, field_perms, has_field_config, view_all_fields):
                            continue

                        # Skip if field already in obj_data (from model fields)
                        if field_name in obj_data:
                            continue

                        # Try to get the field value from various sources
                        field_value = None

                        # First check if it's in metadata (for metadata fields)
                        if hasattr(obj, 'metadata') and isinstance(obj.metadata, dict):
                            if field_name in obj.metadata:
                                field_value = obj.metadata.get(field_name)
                                obj_data[field_name] = field_value if field_value is not None else ''
                                continue

                        # Check if it's a property or method on the model instance
                        if hasattr(obj, field_name):
                            attr = getattr(type(obj), field_name, None)
                            if isinstance(attr, property):
                                # It's a property, get its value
                                field_value = getattr(obj, field_name)
                            elif hasattr(obj, field_name):
                                value = getattr(obj, field_name)
                                if callable(value):
                                    # It's a method, call it
                                    try:
                                        field_value = value()
                                    except:
                                        field_value = None
                                else:
                                    field_value = value
                        # Check if it's a method on the metadata class
                        elif hasattr(metadata_class, field_name):
                            metadata_instance = metadata_class()
                            method = getattr(metadata_instance, field_name)
                            if callable(method):
                                try:
                                    field_value = method(obj)
                                except:
                                    field_value = None

                        # Add the field to obj_data
                        # Always add the field, even if it's None or empty string
                        # This ensures metadata fields show up in the form
                        if field_value is not None:
                            obj_data[field_name] = field_value
                        else:
                            # Field not found, set to empty string for form fields
                            obj_data[field_name] = ''
            
            # Prepare fieldsets for display (React component expects array of arrays)
            # Filter fields by read permission to hide restricted fields from UI
            fieldsets = []
            if hasattr(metadata_class, 'fieldsets'):
                for fieldset_name, fieldset_config in metadata_class.fieldsets:
                    field_names = fieldset_config.get('fields', [])

                    # Filter out fields user doesn't have read permission for
                    # Uses helper to correctly handle view_all_fields + field_permissions
                    field_names = [
                        f for f in field_names
                        if _is_field_readable(f, field_perms, has_field_config, view_all_fields)
                    ]

                    if field_names:
                        fieldsets.append([
                            fieldset_name,
                            {'fields': field_names}
                        ])
            
            # Serialize form if available
            form_data = {}
            if hasattr(metadata_class, 'form') and metadata_class.form:
                form_data = serialize_form_for_react(
                    metadata_class.form,
                    user=request.user,
                    instance=obj,
                    model_name=model_name_lower
                )

            # Filter app metadata based on user's group and profile permissions (OR logic)
            group_filtered = filter_app_metadata_by_user_groups(settings.APP_METADATA_SETTINGS, request.user)
            profile_filtered = filter_app_metadata_by_user_profile(settings.APP_METADATA_SETTINGS, request.user)
            filtered_settings = merge_filtered_settings(group_filtered, profile_filtered, settings.APP_METADATA_SETTINGS)

            # Process detail_actions with component-based approach
            detail_actions = []
            if hasattr(metadata_class, 'detail_actions') and metadata_class.detail_actions:
                for action_group in metadata_class.detail_actions:
                    processed_group = []
                    for action in action_group:
                        # Process action with URL substitution for {id} and {field_name} patterns
                        action_copy = action.copy()
                        
                        # Process component props if they exist
                        if 'props' in action_copy:
                            props_copy = action_copy['props'].copy()
                            # Substitute placeholders in props
                            for key, value in props_copy.items():
                                if isinstance(value, str):
                                    # Replace {id} with actual object ID
                                    value = value.replace('{id}', str(obj.id))
                                    # Replace {field_name} with actual field values
                                    for field_name in model._meta.fields:
                                        field_value = getattr(obj, field_name.name, '')
                                        value = value.replace(f'{{{field_name.name}}}', str(field_value))
                                    props_copy[key] = value
                            action_copy['props'] = props_copy
                        
                        processed_group.append(action_copy)
                    detail_actions.append(processed_group)
            
            # Process inline configurations
            inlines_data = []
            if hasattr(metadata_class, 'inlines') and metadata_class.inlines:
                for inline_class in metadata_class.inlines:
                    # Get the inline model
                    inline_model = inline_class.model
                    
                    # Get fields to display from inline configuration (moved outside to avoid UnboundLocalError)
                    inline_fields = []
                    if hasattr(inline_class, 'fields'):
                        inline_fields = inline_class.fields
                    elif hasattr(inline_class, 'readonly_fields'):
                        inline_fields = inline_class.readonly_fields
                    
                    # Initialize inline items
                    inline_items = []
                    
                    # Determine the relationship type using Django field introspection
                    relationship_type = None
                    is_through_model = False
                    parent_field = None
                    
                    # First check if this inline model is a through model for a ManyToMany field
                    for m2m_field in model._meta.many_to_many:
                        if m2m_field.remote_field.through == inline_model:
                            # This is a through model for a ManyToMany relationship
                            relationship_type = "many_to_many"
                            is_through_model = True
                            # Find the field that points back to the parent model
                            for field in inline_model._meta.fields:
                                if field.related_model == model:
                                    parent_field = field.name
                                    break
                            break
                    
                    # If not a through model, check for direct foreign key field
                    if not relationship_type:
                        fk_field = None
                        for field in inline_model._meta.fields:
                            if field.related_model == model:
                                fk_field = field.name
                                # This is a ForeignKey relationship (OneToMany from parent's perspective)
                                relationship_type = "one_to_many"
                                break
                    else:
                        # For backward compatibility, set fk_field for through models
                        fk_field = None
                    
                    # Fetch related objects based on the relationship type
                    if fk_field:
                        # Direct foreign key relationship
                        filter_kwargs = {fk_field: obj}
                        # Check if the model has an objects manager
                        if hasattr(inline_model, 'objects'):
                            related_objects = inline_model.objects.filter(**filter_kwargs)
                        elif hasattr(inline_model, 'owned'):
                            # Use owned manager if available
                            related_objects = inline_model.owned.filter(**filter_kwargs)
                        else:
                            related_objects = []
                    elif is_through_model and parent_field:
                        # Through model for ManyToMany
                        filter_kwargs = {parent_field: obj}
                        # Check if the model has an objects manager
                        if hasattr(inline_model, 'objects'):
                            related_objects = inline_model.objects.filter(**filter_kwargs)
                        elif hasattr(inline_model, 'owned'):
                            # Use owned manager if available
                            related_objects = inline_model.owned.filter(**filter_kwargs)
                        else:
                            related_objects = []
                    else:
                        # No relationship found, skip this inline
                        related_objects = []
                    
                    # Serialize inline objects
                    for related_obj in related_objects:
                        item_data = {
                            'id': str(related_obj.id) if hasattr(related_obj, 'id') else None,
                        }
                        
                        # Add field values
                        for field_name in inline_fields:
                            if field_name == 'object_link':
                                # Special handling for object_link
                                item_data[field_name] = str(related_obj)
                            elif hasattr(related_obj, field_name):
                                value = getattr(related_obj, field_name)
                                # Handle different field types
                                if hasattr(value, 'id'):  # Foreign key
                                    item_data[field_name] = {
                                        'id': str(value.id),
                                        'name': str(value)
                                    }
                                elif callable(value):  # Method
                                    try:
                                        item_data[field_name] = value()
                                    except:
                                        item_data[field_name] = None
                                else:
                                    item_data[field_name] = value
                        
                        inline_items.append(item_data)
                    
                    # Build inline configuration
                    inline_config = {
                        'model_name': inline_model.__name__,
                        'verbose_name': getattr(inline_class, 'verbose_name', inline_model.__name__) or inline_model.__name__,
                        'verbose_name_plural': getattr(inline_class, 'verbose_name_plural', f"{inline_model.__name__}s") or f"{inline_model.__name__}s",
                        'fields': inline_fields,
                        'readonly_fields': getattr(inline_class, 'readonly_fields', []),
                        'can_delete': getattr(inline_class, 'can_delete', True),
                        'items': inline_items,
                        'relationship_type': relationship_type  # Add the relationship type for frontend UI
                    }
                    
                    inlines_data.append(inline_config)
            
            context = {
                'object': obj,
                'object_data': obj_data,  # Pass as Python dict, not JSON string
                'object_data_json': json.dumps(obj_data, cls=DjangoJSONEncoder),  # Also provide JSON version
                'fieldsets': fieldsets,  # Pass as Python list, not JSON string
                'fieldsets_json': json.dumps(fieldsets, cls=DjangoJSONEncoder),  # Also provide JSON version
                'form_data': form_data,  # Pass as Python dict
                'form_data_json': json.dumps(form_data, cls=DjangoJSONEncoder),  # Also provide JSON version
                'detail_actions': detail_actions,  # Pass detail actions as Python list
                'detail_actions_json': json.dumps(detail_actions, cls=DjangoJSONEncoder),  # Also provide JSON version
                'inlines': inlines_data,  # Pass inline data as Python list
                'inlines_json': json.dumps(inlines_data, cls=DjangoJSONEncoder),  # Also provide JSON version
                'model_name': model_name,
                'model_name_lower': model_name_lower,
                'title': f'{model_name} Detail',
                'app_metadata_settings_json': json.dumps(convert_keys_to_camel_case(resolve_urls_in_app_metadata(filtered_settings))),
                # Add model-specific context for app templates
                f'{model_name_lower}': obj,
                f'{model_name_lower}_dict': json.dumps(obj_data, cls=DjangoJSONEncoder),
                f'{model_name_lower}_id': obj.id,
            }
            
            # Try to use app-specific template, fall back to generic
            template_names = [
                f'{model._meta.app_label}/{model_name_lower}_detail.html',
                'core/base_detail_view.html',
                'core/generic_detail_view.html'
            ]
            
            # Use the first available template
            from django.template import TemplateDoesNotExist
            last_error = None
            for template_name in template_names:
                try:
                    return render(request, template_name, context)
                except TemplateDoesNotExist:
                    continue
                except Exception as e:
                    # Store the error but continue trying other templates
                    last_error = e
                    continue
            
            # If we had a rendering error (not just missing templates), raise it
            if last_error:
                raise last_error
            
            # If no template found, return JSON response
            return JsonResponse({'object': obj_data, 'fieldsets': fieldsets, 'inlines': inlines_data}, encoder=DjangoJSONEncoder)
        
        # Set a meaningful name for the view function
        detail_view.__name__ = f'{model.__name__.lower()}_detailview'
        return detail_view
    
    @staticmethod
    def create_create_view(model, metadata_class):
        """
        Create a generic create view for a model (AJAX-based).
        
        Args:
            model: The Django model class
            metadata_class: The metadata configuration class
            
        Returns:
            A view function for creating new model instances via AJAX
        """
        @login_required
        @require_http_methods(["GET", "POST"])
        def create_view(request):
            # Get the model name
            model_name = model.__name__
            model_name_lower = camel_to_snake(model_name)
            app_label = model._meta.app_label
            permission = f'{app_label}.add_{model_name_lower}'

            # Check create permission using OR logic across three permission layers
            # Superusers bypass permission checks
            if not request.user.is_superuser:
                # Check all three permission layers (OR logic)
                django_granted = request.user.has_perm(permission)
                groups_granted = check_group_permission(request.user, model_name_lower, settings.APP_METADATA_SETTINGS)
                profiles_granted = check_profile_permission(request.user, model_name_lower, 'allow_create', settings.APP_METADATA_SETTINGS)

                # Use OR logic: if ANY permission check passes, grant access
                if not (django_granted or groups_granted or profiles_granted):
                    # All three checks failed - deny access
                    raise Http404()

            # Handle GET request - return form metadata
            if request.method == 'GET':
                # Get field permissions
                # Note: view_all_fields only affects read access, not edit access for create forms
                field_perms, has_field_config, _view_all_fields = get_user_field_permissions(request.user, model_name_lower, settings.APP_METADATA_SETTINGS)

                # Get the form class from metadata if available
                form_class = getattr(metadata_class, 'form', None)

                # Fallback to trying to import form by convention
                if not form_class:
                    try:
                        forms_module = __import__(f'{model._meta.app_label}.forms', fromlist=[f'{model_name}Form'])
                        form_class = getattr(forms_module, f'{model_name}Form', None)
                    except (ImportError, AttributeError):
                        pass

                # Generate form fields metadata
                form_fields = []
                if form_class:
                    # Create a dummy form instance to inspect fields
                    # Try to pass user for context-aware filtering
                    try:
                        dummy_form = form_class(user=request.user)
                    except TypeError:
                        # Form doesn't accept user parameter, use without it
                        dummy_form = form_class()
                    for field_name, field in dummy_form.fields.items():
                        # Check field permission - only include editable fields in create form
                        # Note: view_all_fields does NOT grant edit access
                        if has_field_config:
                            if field_name not in field_perms:
                                # Field not in whitelist - exclude from create form
                                continue
                            if not field_perms[field_name].get('editable', True):
                                # Field explicitly not editable - exclude from create form
                                continue

                        field_info = {
                            'name': field_name,
                            'label': field.label or field_name.replace('_', ' ').title(),
                            'required': field.required,
                            'type': 'text'  # Default type
                        }

                        # Map Django field types to HTML input types
                        from django.forms import Textarea, EmailField, URLField, IntegerField, DecimalField, DateField, DateTimeField, BooleanField, ChoiceField, Select
                        if isinstance(field.widget, Textarea):
                            field_info['type'] = 'textarea'
                        elif isinstance(field.widget, Select) or isinstance(field, ChoiceField):
                            field_info['type'] = 'select'
                            # Add choices for select fields
                            if hasattr(field, 'choices'):
                                field_info['choices'] = [
                                    {'value': str(choice[0]), 'label': str(choice[1])}
                                    for choice in field.choices
                                ]
                        elif isinstance(field, EmailField):
                            field_info['type'] = 'email'
                        elif isinstance(field, URLField):
                            field_info['type'] = 'url'
                        elif isinstance(field, (IntegerField, DecimalField)):
                            field_info['type'] = 'number'
                        elif isinstance(field, DateField):
                            field_info['type'] = 'date'
                        elif isinstance(field, DateTimeField):
                            field_info['type'] = 'datetime-local'
                        elif isinstance(field, BooleanField):
                            field_info['type'] = 'checkbox'

                        # Get default value if available
                        if field.initial is not None:
                            field_info['default'] = field.initial

                        form_fields.append(field_info)
                else:
                    # Default fields if no form class
                    form_fields = [
                        {'name': 'name', 'label': 'Name', 'type': 'text', 'required': True}
                    ]
                    
                    # Add description field if model has it
                    if hasattr(model, 'description'):
                        form_fields.append({'name': 'description', 'label': 'Description', 'type': 'textarea', 'required': False})
                
                return JsonResponse({
                    'form_fields': form_fields,
                    'model_name': model_name
                })
            
            # Handle POST request - create the record
            # Get field permissions for validation
            # Note: view_all_fields only affects read access, not edit access
            field_perms, has_field_config, _view_all_fields = get_user_field_permissions(request.user, model_name_lower, settings.APP_METADATA_SETTINGS)

            # Validate field permissions before processing
            # Note: view_all_fields does NOT grant edit access
            if has_field_config:
                forbidden_fields = []
                for field_name in request.POST.keys():
                    # Skip CSRF token and other non-field data
                    if field_name in ['csrfmiddlewaretoken', 'metadata']:
                        continue
                    # Check if field is in whitelist and editable
                    if field_name not in field_perms:
                        # Field not in whitelist
                        forbidden_fields.append(field_name)
                    elif not field_perms[field_name].get('editable', True):
                        # Field explicitly not editable
                        forbidden_fields.append(field_name)

                if forbidden_fields:
                    return JsonResponse({
                        'success': False,
                        'error': f'You do not have permission to set the following fields: {", ".join(forbidden_fields)}'
                    }, status=403)

            # Get the form class from metadata if available
            form_class = getattr(metadata_class, 'form', None)

            # Fallback to trying to import form by convention
            if not form_class:
                try:
                    forms_module = __import__(f'{model._meta.app_label}.forms', fromlist=[f'{model_name}Form'])
                    form_class = getattr(forms_module, f'{model_name}Form', None)
                except (ImportError, AttributeError):
                    pass

            if form_class:
                # Prepare POST data for form
                post_data = request.POST.copy()

                # Debug logging
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"CREATE VIEW DEBUG - POST data received: {dict(post_data)}")
                logger.error(f"CREATE VIEW DEBUG - Form class: {form_class.__name__}")

                # Check if this form uses MetadataMixin
                if hasattr(form_class, 'metadata_fields'):
                    logger.error(f"CREATE VIEW DEBUG - Form has metadata_fields: {form_class.metadata_fields}")

                    # Remove corrupted metadata field if it's '[object Object]'
                    if 'metadata' in post_data and post_data['metadata'] == '[object Object]':
                        del post_data['metadata']
                        logger.error("CREATE VIEW DEBUG - Removed corrupted metadata field '[object Object]'")

                    # Initialize empty metadata if not present
                    if 'metadata' not in post_data:
                        import json
                        post_data['metadata'] = json.dumps({})
                        logger.error(f"CREATE VIEW DEBUG - Added empty metadata to POST: {post_data['metadata']}")

                # Create new instance using the form
                # Try to pass user for context-aware filtering
                try:
                    form = form_class(post_data, user=request.user)
                except TypeError:
                    # Form doesn't accept user parameter, use without it
                    form = form_class(post_data)

                # Set owner if the model has an owner field
                if hasattr(model, 'owner') and hasattr(form.instance, 'owner'):
                    form.instance.owner = request.user

                if form.is_valid():
                    obj = form.save()
                    return JsonResponse({
                        'success': True, 
                        'message': f'{model_name} created successfully',
                        'id': str(obj.id) if hasattr(obj, 'id') else None
                    })
                else:
                    logger.error(f"CREATE VIEW DEBUG - Form errors: {form.errors}")
                    logger.error(f"CREATE VIEW DEBUG - Form data after init: {form.data}")
                    # Include debug info in response for browser console
                    debug_info = {
                        'post_data_received': dict(post_data),
                        'form_errors': dict(form.errors),
                        'form_class': form_class.__name__,
                        'metadata_fields': getattr(form_class, 'metadata_fields', None),
                    }
                    return JsonResponse({
                        'success': False, 
                        'errors': form.errors,
                        'debug': debug_info
                    }, status=400)
            else:
                # Direct creation without form
                obj = model()
                
                # Set owner if the model has an owner field
                if hasattr(obj, 'owner'):
                    obj.owner = request.user
                
                # Set fields from POST data
                for field_name, value in request.POST.items():
                    if hasattr(obj, field_name) and field_name not in ['id', 'owner', 'created_at', 'updated_at']:
                        setattr(obj, field_name, value)
                
                try:
                    obj.save()
                    return JsonResponse({
                        'success': True, 
                        'message': f'{model_name} created successfully',
                        'id': str(obj.id) if hasattr(obj, 'id') else None
                    })
                except Exception as e:
                    return JsonResponse({'success': False, 'error': str(e)}, status=400)
        
        # Set a meaningful name for the view function
        create_view.__name__ = f'{model.__name__.lower()}_create'
        return create_view
    
    @staticmethod
    def create_update_view(model, metadata_class):
        """
        Create a generic update view for a model (AJAX-based).
        
        Args:
            model: The Django model class
            metadata_class: The metadata configuration class
            
        Returns:
            A view function for updating model instances via AJAX
        """
        @login_required
        @require_http_methods(["POST"])
        def update_view(request, **kwargs):
            # Get the model name and ID parameter
            model_name = model.__name__
            model_name_lower = camel_to_snake(model_name)
            id_param = f'{model_name_lower}_id'
            app_label = model._meta.app_label
            permission = f'{app_label}.change_{model_name_lower}'

            # Check edit permission using OR logic across three permission layers
            # Superusers bypass permission checks
            if not request.user.is_superuser:
                # Check all three permission layers (OR logic)
                django_granted = request.user.has_perm(permission)
                groups_granted = check_group_permission(request.user, model_name_lower, settings.APP_METADATA_SETTINGS)
                profiles_granted = check_profile_permission(request.user, model_name_lower, 'allow_edit', settings.APP_METADATA_SETTINGS)

                # Use OR logic: if ANY permission check passes, grant access
                if not (django_granted or groups_granted or profiles_granted):
                    # All three checks failed - deny access
                    raise Http404()

            # Get the object ID from kwargs
            object_id = kwargs.get(id_param)
            if not object_id:
                return JsonResponse({'error': f'No {model_name} ID provided'}, status=400)
            
            # Get the object with ownership check using helper method
            try:
                queryset = _get_user_queryset(model, request.user)
                obj = queryset.get(id=object_id)
            except model.DoesNotExist:
                return JsonResponse({'error': f'{model_name} not found'}, status=404)

            # Get field permissions for validation
            # Note: view_all_fields only affects read access, not edit access
            field_perms, has_field_config, _view_all_fields = get_user_field_permissions(request.user, model_name_lower, settings.APP_METADATA_SETTINGS)

            # Validate field permissions before processing
            # Note: view_all_fields does NOT grant edit access
            if has_field_config:
                forbidden_fields = []
                for field_name in request.POST.keys():
                    # Skip CSRF token and other non-field data
                    if field_name in ['csrfmiddlewaretoken', 'metadata']:
                        continue
                    # Check if field is in whitelist and editable
                    if field_name not in field_perms:
                        # Field not in whitelist
                        forbidden_fields.append(field_name)
                    elif not field_perms[field_name].get('editable', True):
                        # Field explicitly not editable
                        forbidden_fields.append(field_name)

                if forbidden_fields:
                    return JsonResponse({
                        'success': False,
                        'error': f'You do not have permission to edit the following fields: {", ".join(forbidden_fields)}'
                    }, status=403)

            # Get the form class from metadata if available
            form_class = getattr(metadata_class, 'form', None)

            # Fallback to trying to import form by convention
            if not form_class:
                try:
                    forms_module = __import__(f'{model._meta.app_label}.forms', fromlist=[f'{model_name}Form'])
                    form_class = getattr(forms_module, f'{model_name}Form', None)
                except (ImportError, AttributeError):
                    pass

            if form_class:
                # Prepare POST data for form
                # If the form has metadata_fields, we need to handle them specially
                post_data = request.POST.copy()

                # Check if this form uses MetadataMixin
                if hasattr(form_class, 'metadata_fields'):
                    # Remove corrupted metadata field if it's '[object Object]'
                    if 'metadata' in post_data and post_data['metadata'] == '[object Object]':
                        del post_data['metadata']

                    # Add the current metadata to POST data if not present
                    if 'metadata' not in post_data and hasattr(obj, 'metadata'):
                        current_metadata = obj.metadata if obj.metadata else {}
                        post_data['metadata'] = json.dumps(current_metadata)

                # Use the form for validation and saving
                form = form_class(post_data, instance=obj)
                if form.is_valid():
                    form.save()
                    return JsonResponse({'success': True, 'message': f'{model_name} updated successfully'})
                else:
                    # Include debug info in response for browser console
                    debug_info = {
                        'post_data_received': dict(post_data),
                        'form_errors': dict(form.errors),
                        'form_class': form_class.__name__,
                        'metadata_fields': getattr(form_class, 'metadata_fields', None),
                        'instance_metadata': obj.metadata if hasattr(obj, 'metadata') else None,
                    }
                    return JsonResponse({
                        'success': False, 
                        'errors': form.errors,
                        'debug': debug_info
                    }, status=400)
            else:
                # Direct update without form
                for field_name, value in request.POST.items():
                    if hasattr(obj, field_name) and field_name not in ['id', 'owner', 'created_at', 'updated_at']:
                        setattr(obj, field_name, value)
                
                try:
                    obj.save()
                    return JsonResponse({'success': True, 'message': f'{model_name} updated successfully'})
                except Exception as e:
                    return JsonResponse({'success': False, 'error': str(e)}, status=400)
        
        # Set a meaningful name for the view function
        update_view.__name__ = f'{model.__name__.lower()}_update'
        return update_view
    
    def create_inline_update_view(self, model, metadata_class):
        """
        Create a generic inline update view for managing M2M relationships.
        
        Args:
            model: The Django model class
            metadata_class: The metadata configuration class
            
        Returns:
            A view function for updating inline relationships via AJAX
        """
        @login_required
        @require_http_methods(["POST"])
        def inline_update_view(request, **kwargs):
            import json
            import logging
            logger = logging.getLogger(__name__)
            
            # Get the model name and ID parameter
            model_name = model.__name__
            model_name_lower = camel_to_snake(model_name)
            id_param = f'{model_name_lower}_id'
            inline_model_name = kwargs.get('inline_model')
            
            # Get the object ID from kwargs
            object_id = kwargs.get(id_param)
            if not object_id:
                return JsonResponse({'error': f'No {model_name} ID provided'}, status=400)
            
            if not inline_model_name:
                return JsonResponse({'error': 'No inline model specified'}, status=400)

            # Get the object with ownership check using helper method
            try:
                queryset = _get_user_queryset(model, request.user)
                obj = queryset.get(id=object_id)
            except model.DoesNotExist:
                return JsonResponse({'error': f'{model_name} not found'}, status=404)

            # Parse request body
            try:
                data = json.loads(request.body)
                add_ids = data.get('add', [])
                remove_ids = data.get('remove', [])
            except (json.JSONDecodeError, KeyError) as e:
                return JsonResponse({'error': f'Invalid request data: {str(e)}'}, status=400)
            
            # Find the inline configuration
            inline_class = None
            if hasattr(metadata_class, 'inlines') and metadata_class.inlines:
                for inline in metadata_class.inlines:
                    if inline.model.__name__.lower() == inline_model_name.lower():
                        inline_class = inline
                        break
            
            if not inline_class:
                return JsonResponse({'error': f'Inline model {inline_model_name} not found'}, status=404)
            
            # Get the inline model
            inline_model = inline_class.model
            
            # Determine the relationship type and field names
            # Check if this is a through model for M2M
            is_through_model = False
            parent_field = None
            related_field = None
            m2m_field = None
            
            # First check for direct M2M fields on the parent model
            for field in model._meta.many_to_many:
                if field.remote_field.through == inline_model:
                    m2m_field = field.name
                    is_through_model = True
                    # Find the field that points to the related model
                    for through_field in inline_model._meta.fields:
                        if through_field.related_model == model:
                            parent_field = through_field.name
                        elif through_field.related_model and through_field.related_model != model:
                            related_field = through_field.name
                    break
            
            if not is_through_model:
                # Check if it's a direct FK relationship
                for field in inline_model._meta.fields:
                    if field.related_model == model:
                        parent_field = field.name
                        break
            
            if not parent_field and not m2m_field:
                return JsonResponse({'error': 'Could not determine relationship type'}, status=400)
            
            try:
                # Handle M2M relationships
                if m2m_field:
                    m2m_manager = getattr(obj, m2m_field)
                    
                    # Convert string IDs to UUID objects if needed
                    from uuid import UUID
                    
                    # Add new items
                    if add_ids:
                        # Convert string UUIDs to UUID objects
                        uuid_add_ids = []
                        for id_str in add_ids:
                            try:
                                uuid_add_ids.append(UUID(id_str))
                            except (ValueError, TypeError):
                                # If it's already a UUID or can't be converted, use as is
                                uuid_add_ids.append(id_str)
                        m2m_manager.add(*uuid_add_ids)
                    
                    # Remove items
                    if remove_ids:
                        # Convert string UUIDs to UUID objects
                        uuid_remove_ids = []
                        for id_str in remove_ids:
                            try:
                                uuid_remove_ids.append(UUID(id_str))
                            except (ValueError, TypeError):
                                # If it's already a UUID or can't be converted, use as is
                                uuid_remove_ids.append(id_str)
                        m2m_manager.remove(*uuid_remove_ids)
                    
                    # Return updated inline data
                    updated_items = []
                    for item in m2m_manager.all():
                        updated_items.append({
                            'id': str(item.id),
                            'name': str(item)
                        })
                    
                    return JsonResponse({
                        'success': True,
                        'message': f'{inline_model_name} updated successfully',
                        'items': updated_items
                    })
                
                # Handle direct FK relationships (if needed in future)
                else:
                    return JsonResponse({'error': 'Direct FK relationship updates not yet implemented'}, status=400)
                
            except Exception as e:
                logger.error(f"Error updating inline {inline_model_name}: {str(e)}")
                return JsonResponse({'error': f'Failed to update: {str(e)}'}, status=500)
        
        # Set a meaningful name for the view function
        inline_update_view.__name__ = f'{model.__name__.lower()}_inline_update'
        return inline_update_view
    
    def create_available_items_view(self, model, metadata_class):
        """
        Create a view to fetch available items for inline relationships.
        
        Args:
            model: The Django model class
            metadata_class: The metadata configuration class
            
        Returns:
            A view function for fetching available items for inline relationships
        """
        @login_required
        def available_items_view(request, **kwargs):
            import json
            
            # Get the model name and ID parameter
            model_name = model.__name__
            model_name_lower = camel_to_snake(model_name)
            id_param = f'{model_name_lower}_id'
            inline_type = kwargs.get('inline_type')
            
            # Get the object ID from kwargs
            object_id = kwargs.get(id_param)
            if not object_id:
                return JsonResponse({'error': f'No {model_name} ID provided'}, status=400)

            # Get the object with ownership check using helper method
            try:
                queryset = _get_user_queryset(model, request.user)
                obj = queryset.get(id=object_id)
            except model.DoesNotExist:
                return JsonResponse({'error': f'{model_name} not found'}, status=404)

            # Generic handling for any ManyToMany field
            # Try to find the M2M field that matches the inline_type
            m2m_field = None
            related_model = None
            
            # Check all many-to-many fields on the model
            for field in model._meta.many_to_many:
                # Check if field name matches inline_type (with or without 's')
                field_name = field.name
                if field_name == inline_type or field_name == inline_type.rstrip('s'):
                    m2m_field = field
                    related_model = field.related_model
                    break
            
            if m2m_field and related_model:
                # Get the M2M manager
                m2m_manager = getattr(obj, m2m_field.name)
                
                # Get all current items in the relationship
                current_items = m2m_manager.all()
                current_item_ids = [item.id for item in current_items]
                
                # Get all available items (excluding current ones)
                all_items = related_model.objects.exclude(id__in=current_item_ids)
                
                # Build the response
                items = []
                for item in all_items:
                    item_data = {
                        'id': str(item.id),
                        'name': str(item),
                    }
                    
                    # Add email if available (for User-related models)
                    if hasattr(item, 'user') and hasattr(item.user, 'email'):
                        item_data['email'] = item.user.email
                    elif hasattr(item, 'email'):
                        item_data['email'] = item.email
                    
                    # Add any other useful fields
                    if hasattr(item, 'description'):
                        item_data['description'] = item.description
                    
                    items.append(item_data)
                
                return JsonResponse({'items': items})
            
            # If no matching M2M field found, return empty list
            return JsonResponse({'items': []})
        
        # Set a meaningful name for the view function
        available_items_view.__name__ = f'{model.__name__.lower()}_available_items'
        return available_items_view
    
    @staticmethod
    def create_delete_view(model, metadata_class):
        """
        Create a generic delete view for a model.
        
        Args:
            model: The Django model class
            metadata_class: The metadata configuration class
            
        Returns:
            A view function for deleting model instances
        """
        @login_required
        @require_http_methods(["POST"])
        def delete_view(request, **kwargs):
            # Get the model name and ID parameter
            model_name = model.__name__
            model_name_lower = camel_to_snake(model_name)
            id_param = f'{model_name_lower}_id'
            app_label = model._meta.app_label
            permission = f'{app_label}.delete_{model_name_lower}'

            # Check delete permission using OR logic across three permission layers
            # Superusers bypass permission checks
            if not request.user.is_superuser:
                # Check all three permission layers (OR logic)
                django_granted = request.user.has_perm(permission)
                groups_granted = check_group_permission(request.user, model_name_lower, settings.APP_METADATA_SETTINGS)
                profiles_granted = check_profile_permission(request.user, model_name_lower, 'allow_delete', settings.APP_METADATA_SETTINGS)

                # Use OR logic: if ANY permission check passes, grant access
                if not (django_granted or groups_granted or profiles_granted):
                    # All three checks failed - deny access
                    raise Http404()

            # Get the object ID from kwargs
            object_id = kwargs.get(id_param)
            if not object_id:
                return JsonResponse({'error': f'No {model_name} ID provided'}, status=400)

            # Get the object with ownership check using helper method
            try:
                queryset = _get_user_queryset(model, request.user)
                obj = queryset.get(id=object_id)
            except model.DoesNotExist:
                return JsonResponse({'error': f'{model_name} not found'}, status=404)

            # Try to delete the object
            try:
                # Store the name for the success message
                obj_name = getattr(obj, 'name', str(obj))
                
                # Delete the object (Django handles cascading deletes automatically)
                obj.delete()
                
                # Return success response with redirect URL
                return JsonResponse({
                    'success': True,
                    'message': f'{model_name} "{obj_name}" deleted successfully',
                    'redirect_url': f'/m/{model_name_lower}/list'
                })
            except Exception as e:
                # Handle any deletion errors (e.g., protected foreign keys)
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Error deleting {model_name} {object_id}: {str(e)}")
                
                return JsonResponse({
                    'success': False,
                    'error': f'Unable to delete {model_name}. It may have dependent records.'
                }, status=400)
        
        # Set a meaningful name for the view function
        delete_view.__name__ = f'{model.__name__.lower()}_delete'
        return delete_view


class LegacyRedirectView:
    """
    View that redirects legacy URLs (without app prefix) to new app-prefixed URLs.

    This enables backwards compatibility while migrating to the new URL structure.
    Legacy format: /m/model_name/list or /r/model_name/{id}/view
    New format: /app/{app_name}/m/model_name/list or /app/{app_name}/r/model_name/{id}/view

    Note: All URLs use snake_case for model names.
    """

    def __init__(self, app_name, model_name, pattern_type):
        """
        Initialize the redirect view.

        Args:
            app_name: The app this model belongs to (e.g., 'classroom', 'cms')
            model_name: The model name in snake_case (e.g., 'course', 'blog_post')
            pattern_type: Type of URL pattern ('list', 'detail', 'create', 'update',
                         'inline_update', 'available_items', 'delete')
        """
        self.app_name = app_name
        self.model_name = model_name
        self.pattern_type = pattern_type

    @classmethod
    def as_view(cls, **initkwargs):
        """
        Return a view function that redirects to the new app-prefixed URL.
        """
        def view(request, **kwargs):
            from django.http import HttpResponseRedirect

            # Get instance parameters
            app_name = initkwargs.get('app_name')
            model_name = initkwargs.get('model_name')
            pattern_type = initkwargs.get('pattern_type')

            # Build the new URL based on pattern type
            # Note: model_name is already in snake_case
            if pattern_type == 'list':
                new_url = f'/app/{app_name}/m/{model_name}/list'
            elif pattern_type == 'detail':
                record_id = kwargs.get(f'{model_name}_id')
                new_url = f'/app/{app_name}/r/{model_name}/{record_id}/view'
            elif pattern_type == 'create':
                new_url = f'/app/{app_name}/m/{model_name}/create'
            elif pattern_type == 'update':
                record_id = kwargs.get(f'{model_name}_id')
                new_url = f'/app/{app_name}/r/{model_name}/{record_id}/update'
            elif pattern_type == 'inline_update':
                record_id = kwargs.get(f'{model_name}_id')
                inline_model = kwargs.get('inline_model')
                new_url = f'/app/{app_name}/r/{model_name}/{record_id}/inline/{inline_model}/update'
            elif pattern_type == 'available_items':
                record_id = kwargs.get(f'{model_name}_id')
                inline_type = kwargs.get('inline_type')
                new_url = f'/app/{app_name}/r/{model_name}/{record_id}/available_{inline_type}/'
            elif pattern_type == 'delete':
                record_id = kwargs.get(f'{model_name}_id')
                new_url = f'/app/{app_name}/r/{model_name}/{record_id}/delete'
            else:
                # Fallback - shouldn't happen
                new_url = f'/app/{app_name}/m/{model_name}/list'

            # Preserve query string if present
            if request.GET:
                from urllib.parse import urlencode
                query_string = urlencode(request.GET)
                new_url = f'{new_url}?{query_string}'

            # Use 302 (temporary) redirect for flexibility
            return HttpResponseRedirect(new_url)

        return view