import json
from django import forms
from django.db.models import ForeignKey, OneToOneField, Q
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse, Http404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.core.serializers.json import DjangoJSONEncoder
from django.core.exceptions import FieldDoesNotExist
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from app import settings
from grit.core.utils.case_conversion import convert_keys_to_camel_case, resolve_urls_in_app_metadata, camel_to_snake
from grit.core.utils.permissions import (
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
    if field_name in field_perms:
        return field_perms[field_name].get('readable', True)
    if view_all_fields:
        return True
    if has_field_config:
        return False
    return True


def _get_inline_field_name(parent_model, inline_model):
    for m2m_field in parent_model._meta.many_to_many:
        if m2m_field.remote_field.through == inline_model:
            return m2m_field.name
    for field in inline_model._meta.fields:
        if field.related_model == parent_model:
            try:
                if hasattr(field, 'remote_field') and field.remote_field:
                    if hasattr(field.remote_field, 'related_query_name'):
                        related_name = field.remote_field.related_query_name()
                        if related_name and callable(related_name) is False:
                            return related_name
                    if hasattr(field.remote_field, 'get_accessor_name'):
                        accessor = field.remote_field.get_accessor_name()
                        if accessor:
                            return accessor
            except (AttributeError, TypeError):
                pass
            return f"{inline_model._meta.model_name}_set"
    return None


def _get_user_queryset(model, user):
    if hasattr(model, 'scoped') and hasattr(model.scoped, 'for_user'):
        return model.scoped.for_user(user)
    if hasattr(model, 'owned'):
        if hasattr(model.owned, 'for_user'):
            return model.owned.for_user(user.id if hasattr(user, 'id') else user)
        else:
            return model.owned.filter(owner=user)
    if hasattr(model, 'objects'):
        if hasattr(model, 'owner'):
            return model.objects.filter(owner=user)
        else:
            return model.objects.all()
    if hasattr(model, 'objects'):
        return model.objects.none()
    from django.db import models as django_models
    return django_models.Manager().none()


def _set_model_field_value(obj, field_name, value, model):
    try:
        field = model._meta.get_field(field_name)
        if isinstance(field, (ForeignKey, OneToOneField)):
            if value == '' and field.null:
                value = None
            setattr(obj, f'{field_name}_id', value)
        else:
            setattr(obj, field_name, value)
        return True
    except FieldDoesNotExist:
        return False


def _process_single_action(action, model_name, model_name_lower, current_app_name):
    if isinstance(action, dict):
        if action.get('action') == 'new' or action.get('name') == 'new':
            url = f'/app/{current_app_name}/m/{model_name_lower}/create' if current_app_name else f'/m/{model_name_lower}/create'
            return ({
                'label': action.get('label', f'New {model_name}'),
                'action': 'create',
                'url': url,
                'method': 'GET'
            }, True)
        elif action.get('action') != 'create':
            return (action, False)
        else:
            return (None, False)
    else:
        if action == 'new':
            url = f'/app/{current_app_name}/m/{model_name_lower}/create' if current_app_name else f'/m/{model_name_lower}/create'
            return ({
                'label': f'New {model_name}',
                'action': 'create',
                'url': url,
                'method': 'GET'
            }, True)
        else:
            return (action, False)


def serialize_form_for_react(form_class, user=None, instance=None, model_name=None):
    if not form_class:
        return {}
    try:
        form_kwargs = {}
        if instance:
            form_kwargs['instance'] = instance
        if user:
            form_kwargs['user'] = user
        form_instance = form_class(**form_kwargs)
    except Exception:
        try:
            form_instance = form_class()
        except Exception:
            return {}
    field_perms = {}
    has_field_config = False
    view_all_fields = False
    if user and model_name:
        field_perms, has_field_config, view_all_fields = get_user_field_permissions(user, model_name, settings.APP_METADATA_SETTINGS)
    form_data = {}
    for field_name, field in form_instance.fields.items():
        if not _is_field_readable(field_name, field_perms, has_field_config, view_all_fields):
            continue
        widget_type = "TextInput"
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
        if has_field_config or view_all_fields:
            if field_name in field_perms:
                if not field_perms[field_name].get('editable', True):
                    field_config["disabled"] = True
            elif view_all_fields:
                field_config["disabled"] = True
            elif has_field_config:
                field_config["disabled"] = True
        if field.help_text:
            field_config["help_text"] = str(field.help_text)
        if hasattr(field, 'choices') and field.choices:
            field_config["choices"] = [
                {"value": str(choice[0]), "label": str(choice[1])}
                for choice in field.choices
                if choice[0] != ''
            ]
        if hasattr(field, 'max_length') and field.max_length:
            field_config["max_length"] = field.max_length
        if hasattr(field, 'min_length') and field.min_length:
            field_config["min_length"] = field.min_length
        if field.label and field.label != field_name.replace('_', ' ').title():
            field_config["label"] = str(field.label)
        form_data[field_name] = field_config
    return form_data


class MetadataViewGenerator:
    @staticmethod
    def create_list_view(model, metadata_class):
        @login_required
        def list_view(request):
            app_label = model._meta.app_label
            model_name = model.__name__
            model_name_lower = camel_to_snake(model_name)
            permission = f'{app_label}.view_{model_name_lower}'
            import re
            app_name_match = re.match(r'^/app/([^/]+)/', request.path)
            current_app_name = app_name_match.group(1) if app_name_match else None
            if not request.user.is_superuser:
                django_granted = request.user.has_perm(permission)
                groups_granted = check_group_permission(request.user, model_name_lower, settings.APP_METADATA_SETTINGS)
                profiles_granted = check_profile_permission(request.user, model_name_lower, 'allow_read', settings.APP_METADATA_SETTINGS)
                if not (django_granted or groups_granted or profiles_granted):
                    raise Http404()
            queryset = _get_user_queryset(model, request.user)
            if hasattr(metadata_class, 'ordering') and metadata_class.ordering:
                queryset = queryset.order_by(*metadata_class.ordering)
            search_query = request.GET.get('search', '').strip()
            if search_query and hasattr(metadata_class, 'list_display'):
                q_objects = Q()
                for field_name in metadata_class.list_display:
                    try:
                        field = model._meta.get_field(field_name)
                        field_type = field.get_internal_type()
                        if field_type in ('CharField', 'TextField', 'EmailField', 'URLField'):
                            q_objects |= Q(**{f"{field_name}__icontains": search_query})
                    except Exception:
                        pass
                if q_objects:
                    queryset = queryset.filter(q_objects)
            try:
                page_size = int(request.GET.get('page_size', 25))
            except (ValueError, TypeError):
                page_size = 25
            page_number = request.GET.get('page', 1)
            page_size = max(1, min(page_size, 100))
            paginator = Paginator(queryset, page_size)
            try:
                page_obj = paginator.page(page_number)
            except PageNotAnInteger:
                page_obj = paginator.page(1)
            except EmptyPage:
                page_obj = paginator.page(paginator.num_pages)
            field_perms, has_field_config, view_all_fields = get_user_field_permissions(request.user, model_name_lower, settings.APP_METADATA_SETTINGS)
            items_data = []
            for item in page_obj:
                item_dict = {
                    'id': str(item.id),
                    'name': getattr(item, 'name', str(item)),
                }
                if hasattr(metadata_class, 'list_display'):
                    for field_name in metadata_class.list_display:
                        if not _is_field_readable(field_name, field_perms, has_field_config, view_all_fields):
                            continue
                        if hasattr(item, field_name):
                            attr = getattr(type(item), field_name, None)
                            if isinstance(attr, property):
                                item_dict[field_name] = getattr(item, field_name)
                            else:
                                value = getattr(item, field_name)
                                if hasattr(value, 'id'):
                                    item_dict[field_name] = str(value)
                                elif callable(value):
                                    item_dict[field_name] = value()
                                else:
                                    item_dict[field_name] = value
                        elif hasattr(item, 'metadata') and item.metadata and field_name in item.metadata:
                            item_dict[field_name] = item.metadata.get(field_name, '')
                if hasattr(item, 'metadata') and item.metadata:
                    if isinstance(item.metadata, dict):
                        for key, value in item.metadata.items():
                            if key not in item_dict:
                                if not _is_field_readable(key, field_perms, has_field_config, view_all_fields):
                                    continue
                                item_dict[key] = value
                items_data.append(item_dict)
            columns = []
            columns.append({'type': 'select'})
            if hasattr(metadata_class, 'list_display') and metadata_class.list_display:
                first_column_added = False
                for field_name in metadata_class.list_display:
                    if not _is_field_readable(field_name, field_perms, has_field_config, view_all_fields):
                        continue
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
                        columns.append({
                            'fieldName': field_name,
                            'label': field_name.replace('_', ' ').title(),
                            'sortable': True
                        })
            else:
                columns.append({
                    'type': 'link',
                    'fieldName': 'name',
                    'label': 'Name',
                    'href': f'/r/{model_name_lower}/{{id}}/view',
                    'linkText': '{name}',
                    'sortable': True
                })
            actions = []
            if hasattr(metadata_class, 'list_actions'):
                actions = metadata_class.list_actions
            processed_actions = []
            has_new_action = False
            if actions and isinstance(actions, list):
                is_grouped = actions and isinstance(actions[0], list)
                action_lists = actions if is_grouped else [actions]
                for group in action_lists:
                    processed_group = []
                    for action in group:
                        processed, is_new = _process_single_action(
                            action, model_name, model_name_lower, current_app_name
                        )
                        if is_new:
                            has_new_action = True
                        if processed is not None:
                            processed_group.append(processed)
                    if processed_group:
                        processed_actions.append(processed_group)
            actions = processed_actions if processed_actions else [[]]
            group_filtered = filter_app_metadata_by_user_groups(settings.APP_METADATA_SETTINGS, request.user)
            profile_filtered = filter_app_metadata_by_user_profile(settings.APP_METADATA_SETTINGS, request.user)
            filtered_settings = merge_filtered_settings(group_filtered, profile_filtered, settings.APP_METADATA_SETTINGS)
            pagination_data = {
                'currentPage': page_obj.number,
                'totalPages': paginator.num_pages,
                'totalItems': paginator.count,
                'pageSize': page_size,
                'hasNext': page_obj.has_next(),
                'hasPrevious': page_obj.has_previous(),
                'nextPage': page_obj.next_page_number() if page_obj.has_next() else None,
                'previousPage': page_obj.previous_page_number() if page_obj.has_previous() else None,
            }
            context = {
                'items': items_data,
                'columns': json.dumps(columns, cls=DjangoJSONEncoder),
                'actions': json.dumps(actions, cls=DjangoJSONEncoder),
                'model_name': model_name,
                'model_name_lower': model_name_lower,
                'title': f'{model_name} List',
                'pagination': pagination_data,
                'pagination_json': json.dumps(pagination_data, cls=DjangoJSONEncoder),
                'search_query': search_query,
                'app_metadata_settings_json': json.dumps(convert_keys_to_camel_case(resolve_urls_in_app_metadata(filtered_settings)))
            }
            template_names = [
                f'{model._meta.app_label}/{model_name_lower}_listview.html',
                'core/base_list_view.html',
                'core/generic_list_view.html'
            ]
            from django.template import TemplateDoesNotExist
            last_error = None
            for template_name in template_names:
                try:
                    return render(request, template_name, context)
                except TemplateDoesNotExist:
                    continue
                except Exception as e:
                    last_error = e
                    continue
            if last_error:
                raise last_error
            raise TemplateDoesNotExist(
                f"No template found for {model_name_lower} list view. Tried: {', '.join(template_names)}"
            )
        list_view.__name__ = f'{model.__name__.lower()}_listview'
        return list_view
    @staticmethod
    def create_detail_view(model, metadata_class):
        @login_required
        def detail_view(request, **kwargs):
            model_name = model.__name__
            model_name_lower = camel_to_snake(model_name)
            id_param = f'{model_name_lower}_id'
            app_label = model._meta.app_label
            permission = f'{app_label}.view_{model_name_lower}'
            if not request.user.is_superuser:
                django_granted = request.user.has_perm(permission)
                groups_granted = check_group_permission(request.user, model_name_lower, settings.APP_METADATA_SETTINGS)
                profiles_granted = check_profile_permission(request.user, model_name_lower, 'allow_read', settings.APP_METADATA_SETTINGS)
                if not (django_granted or groups_granted or profiles_granted):
                    raise Http404()
            object_id = kwargs.get(id_param)
            if not object_id:
                raise Http404(f"No {model_name} ID provided")
            queryset = _get_user_queryset(model, request.user)
            obj = get_object_or_404(queryset, id=object_id)
            field_perms, has_field_config, view_all_fields = get_user_field_permissions(request.user, model_name_lower, settings.APP_METADATA_SETTINGS)
            obj_data = {
                'id': str(obj.id),
                'name': getattr(obj, 'name', str(obj)),
            }
            for field in model._meta.fields:
                field_name = field.name
                if not _is_field_readable(field_name, field_perms, has_field_config, view_all_fields):
                    continue
                value = getattr(obj, field_name)
                if value is None:
                    obj_data[field_name] = None
                elif hasattr(value, 'id'):
                    related_model_name = camel_to_snake(value.__class__.__name__)
                    obj_data[field_name] = {
                        'id': str(value.id),
                        'name': getattr(value, 'name', str(value)),
                        'model': related_model_name
                    }
                elif field.get_internal_type() == 'UUIDField':
                    obj_data[field_name] = str(value)
                elif field.get_internal_type() == 'DateTimeField':
                    obj_data[field_name] = value.isoformat() if value else None
                elif field.get_internal_type() == 'JSONField':
                    obj_data[field_name] = value or {}
                else:
                    obj_data[field_name] = value
            for field in model._meta.many_to_many:
                field_name = field.name
                if not _is_field_readable(field_name, field_perms, has_field_config, view_all_fields):
                    continue
                related_objects = getattr(obj, field_name).all()
                obj_data[field_name] = [
                    {'id': str(item.id), 'name': getattr(item, 'name', str(item))}
                    for item in related_objects
                ]
            if hasattr(obj, 'metadata') and obj.metadata:
                obj_data['metadata'] = obj.metadata
            if hasattr(metadata_class, 'fieldsets') and metadata_class.fieldsets:
                for fieldset_name, fieldset_config in metadata_class.fieldsets:
                    field_names = fieldset_config.get('fields', [])
                    for field_name in field_names:
                        if not _is_field_readable(field_name, field_perms, has_field_config, view_all_fields):
                            continue
                        if field_name in obj_data:
                            continue
                        field_value = None
                        if hasattr(obj, 'metadata') and isinstance(obj.metadata, dict):
                            if field_name in obj.metadata:
                                field_value = obj.metadata.get(field_name)
                                obj_data[field_name] = field_value if field_value is not None else ''
                                continue
                        if hasattr(obj, field_name):
                            attr = getattr(type(obj), field_name, None)
                            if isinstance(attr, property):
                                field_value = getattr(obj, field_name)
                            elif hasattr(obj, field_name):
                                value = getattr(obj, field_name)
                                if callable(value):
                                    try:
                                        field_value = value()
                                    except:
                                        field_value = None
                                else:
                                    field_value = value
                        elif hasattr(metadata_class, field_name):
                            metadata_instance = metadata_class()
                            method = getattr(metadata_instance, field_name)
                            if callable(method):
                                try:
                                    field_value = method(obj)
                                except:
                                    field_value = None
                        if field_value is not None:
                            obj_data[field_name] = field_value
                        else:
                            obj_data[field_name] = ''
            fieldsets = []
            if hasattr(metadata_class, 'fieldsets'):
                for fieldset_name, fieldset_config in metadata_class.fieldsets:
                    field_names = fieldset_config.get('fields', [])
                    field_names = [
                        f for f in field_names
                        if _is_field_readable(f, field_perms, has_field_config, view_all_fields)
                    ]
                    if field_names:
                        fieldsets.append([
                            fieldset_name,
                            {'fields': field_names}
                        ])
            form_data = {}
            if hasattr(metadata_class, 'form') and metadata_class.form:
                form_data = serialize_form_for_react(
                    metadata_class.form,
                    user=request.user,
                    instance=obj,
                    model_name=model_name_lower
                )
            elif hasattr(metadata_class, 'fieldsets') and metadata_class.fieldsets:
                from django.forms import modelform_factory
                fieldset_fields = []
                for fieldset_name, fieldset_config in metadata_class.fieldsets:
                    fieldset_fields.extend(fieldset_config.get('fields', []))
                excluded_fields = {'id', 'created_at', 'updated_at', 'owner', 'metadata'}
                model_field_names = {f.name for f in model._meta.get_fields() if not getattr(f, 'auto_created', False)}
                valid_fields = [f for f in fieldset_fields if f in model_field_names and f not in excluded_fields]
                if valid_fields:
                    DynamicForm = modelform_factory(model, fields=valid_fields)
                    form_data = serialize_form_for_react(
                        DynamicForm,
                        user=request.user,
                        instance=obj,
                        model_name=model_name_lower
                    )
            group_filtered = filter_app_metadata_by_user_groups(settings.APP_METADATA_SETTINGS, request.user)
            profile_filtered = filter_app_metadata_by_user_profile(settings.APP_METADATA_SETTINGS, request.user)
            filtered_settings = merge_filtered_settings(group_filtered, profile_filtered, settings.APP_METADATA_SETTINGS)
            detail_actions = []
            if hasattr(metadata_class, 'detail_actions') and metadata_class.detail_actions:
                for action_group in metadata_class.detail_actions:
                    processed_group = []
                    for action in action_group:
                        action_copy = action.copy()
                        if 'props' in action_copy:
                            props_copy = action_copy['props'].copy()
                            for key, value in props_copy.items():
                                if isinstance(value, str):
                                    value = value.replace('{id}', str(obj.id))
                                    for field_name in model._meta.fields:
                                        field_value = getattr(obj, field_name.name, '')
                                        value = value.replace(f'{{{field_name.name}}}', str(field_value))
                                    props_copy[key] = value
                            action_copy['props'] = props_copy
                        processed_group.append(action_copy)
                    detail_actions.append(processed_group)
            can_summarize = (
                request.user.is_superuser or
                check_profile_permission(request.user, model_name_lower, 'allow_summarize', settings.APP_METADATA_SETTINGS)
            )
            if can_summarize:
                summarize_context = {}
                for field_name, field_value in obj_data.items():
                    if field_name in {'id', 'created_at', 'updated_at', 'owner', 'metadata'}:
                        continue
                    summarize_context[field_name] = field_value
                summarize_action = {
                    'label': 'Summarize',
                    'action': 'summarize',
                    'props': {
                        'context': summarize_context,
                        'modelName': model_name,
                        'recordName': str(obj) if hasattr(obj, '__str__') else obj_data.get('name', '')
                    }
                }
                if detail_actions:
                    detail_actions[0].append(summarize_action)
                else:
                    detail_actions.append([summarize_action])
            inlines_data = []
            if hasattr(metadata_class, 'inlines') and metadata_class.inlines:
                for inline_class in metadata_class.inlines:
                    inline_model = inline_class.model
                    inline_field_name = _get_inline_field_name(model, inline_model)
                    if inline_field_name is not None:
                        if not _is_field_readable(inline_field_name, field_perms, has_field_config, view_all_fields):
                            continue
                    inline_fields = []
                    if hasattr(inline_class, 'fields'):
                        inline_fields = inline_class.fields
                    elif hasattr(inline_class, 'readonly_fields'):
                        inline_fields = inline_class.readonly_fields
                    inline_items = []
                    relationship_type = None
                    is_through_model = False
                    parent_field = None
                    for m2m_field in model._meta.many_to_many:
                        if m2m_field.remote_field.through == inline_model:
                            relationship_type = "many_to_many"
                            is_through_model = True
                            for field in inline_model._meta.fields:
                                if field.related_model == model:
                                    parent_field = field.name
                                    break
                            break
                    if not relationship_type:
                        fk_field = None
                        for field in inline_model._meta.fields:
                            if field.related_model == model:
                                fk_field = field.name
                                relationship_type = "one_to_many"
                                break
                    else:
                        fk_field = None
                    if fk_field:
                        filter_kwargs = {fk_field: obj}
                        if hasattr(inline_model, 'objects'):
                            related_objects = inline_model.objects.filter(**filter_kwargs)
                        elif hasattr(inline_model, 'owned'):
                            related_objects = inline_model.owned.filter(**filter_kwargs)
                        else:
                            related_objects = []
                    elif is_through_model and parent_field:
                        filter_kwargs = {parent_field: obj}
                        if hasattr(inline_model, 'objects'):
                            related_objects = inline_model.objects.filter(**filter_kwargs)
                        elif hasattr(inline_model, 'owned'):
                            related_objects = inline_model.owned.filter(**filter_kwargs)
                        else:
                            related_objects = []
                    else:
                        related_objects = []
                    for related_obj in related_objects:
                        item_data = {
                            'id': str(related_obj.id) if hasattr(related_obj, 'id') else None,
                        }
                        for field_name in inline_fields:
                            if field_name == 'object_link':
                                item_data[field_name] = str(related_obj)
                            elif hasattr(related_obj, field_name):
                                value = getattr(related_obj, field_name)
                                if hasattr(value, 'id'):
                                    item_data[field_name] = {
                                        'id': str(value.id),
                                        'name': str(value)
                                    }
                                elif callable(value):
                                    try:
                                        item_data[field_name] = value()
                                    except:
                                        item_data[field_name] = None
                                else:
                                    item_data[field_name] = value
                        inline_items.append(item_data)
                    inline_config = {
                        'model_name': inline_model.__name__.lower(),
                        'verbose_name': getattr(inline_class, 'verbose_name', inline_model.__name__) or inline_model.__name__,
                        'verbose_name_plural': getattr(inline_class, 'verbose_name_plural', f"{inline_model.__name__}s") or f"{inline_model.__name__}s",
                        'fields': inline_fields,
                        'readonly_fields': getattr(inline_class, 'readonly_fields', []),
                        'can_delete': getattr(inline_class, 'can_delete', True),
                        'items': inline_items,
                        'relationship_type': relationship_type
                    }
                    inlines_data.append(inline_config)
            context = {
                'object': obj,
                'object_data': obj_data,
                'object_data_json': json.dumps(obj_data, cls=DjangoJSONEncoder),
                'fieldsets': fieldsets,
                'fieldsets_json': json.dumps(fieldsets, cls=DjangoJSONEncoder),
                'form_data': form_data,
                'form_data_json': json.dumps(form_data, cls=DjangoJSONEncoder),
                'detail_actions': detail_actions,
                'detail_actions_json': json.dumps(detail_actions, cls=DjangoJSONEncoder),
                'inlines': inlines_data,
                'inlines_json': json.dumps(inlines_data, cls=DjangoJSONEncoder),
                'model_name': model_name,
                'model_name_lower': model_name_lower,
                'title': f'{model_name} Detail',
                'app_metadata_settings_json': json.dumps(convert_keys_to_camel_case(resolve_urls_in_app_metadata(filtered_settings))),
                f'{model_name_lower}': obj,
                f'{model_name_lower}_dict': json.dumps(obj_data, cls=DjangoJSONEncoder),
                f'{model_name_lower}_id': obj.id,
            }
            template_names = [
                f'{model._meta.app_label}/{model_name_lower}_detail.html',
                'core/base_detail_view.html',
                'core/generic_detail_view.html'
            ]
            from django.template import TemplateDoesNotExist
            last_error = None
            for template_name in template_names:
                try:
                    return render(request, template_name, context)
                except TemplateDoesNotExist:
                    continue
                except Exception as e:
                    last_error = e
                    continue
            if last_error:
                raise last_error
            return JsonResponse({'object': obj_data, 'fieldsets': fieldsets, 'inlines': inlines_data}, encoder=DjangoJSONEncoder)
        detail_view.__name__ = f'{model.__name__.lower()}_detailview'
        return detail_view
    @staticmethod
    def create_create_view(model, metadata_class):
        @login_required
        @require_http_methods(["GET", "POST"])
        def create_view(request):
            model_name = model.__name__
            model_name_lower = camel_to_snake(model_name)
            app_label = model._meta.app_label
            permission = f'{app_label}.add_{model_name_lower}'
            if not request.user.is_superuser:
                django_granted = request.user.has_perm(permission)
                groups_granted = check_group_permission(request.user, model_name_lower, settings.APP_METADATA_SETTINGS)
                profiles_granted = check_profile_permission(request.user, model_name_lower, 'allow_create', settings.APP_METADATA_SETTINGS)
                if not (django_granted or groups_granted or profiles_granted):
                    raise Http404()
            if request.method == 'GET':
                field_perms, has_field_config, _view_all_fields = get_user_field_permissions(request.user, model_name_lower, settings.APP_METADATA_SETTINGS)
                form_class = getattr(metadata_class, 'form', None)
                if not form_class:
                    try:
                        forms_module = __import__(f'{model._meta.app_label}.forms', fromlist=[f'{model_name}Form'])
                        form_class = getattr(forms_module, f'{model_name}Form', None)
                    except (ImportError, AttributeError):
                        pass
                form_fields = []
                if form_class:
                    try:
                        dummy_form = form_class(user=request.user)
                    except TypeError:
                        dummy_form = form_class()
                    for field_name, field in dummy_form.fields.items():
                        if has_field_config:
                            if field_name not in field_perms:
                                continue
                            if not field_perms[field_name].get('editable', True):
                                continue
                        field_info = {
                            'name': field_name,
                            'label': field.label or field_name.replace('_', ' ').title(),
                            'required': field.required,
                            'type': 'text'
                        }
                        from django.forms import Textarea, EmailField, URLField, IntegerField, DecimalField, DateField, DateTimeField, BooleanField, ChoiceField, Select
                        if isinstance(field.widget, Textarea):
                            field_info['type'] = 'textarea'
                        elif isinstance(field.widget, Select) or isinstance(field, ChoiceField):
                            field_info['type'] = 'select'
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
                        if field.initial is not None:
                            field_info['default'] = field.initial
                        form_fields.append(field_info)
                else:
                    form_fields = []
                    if hasattr(metadata_class, 'fieldsets') and metadata_class.fieldsets:
                        fieldset_fields = []
                        for fieldset_name, fieldset_config in metadata_class.fieldsets:
                            fieldset_fields.extend(fieldset_config.get('fields', []))
                        excluded_fields = {'id', 'created_at', 'updated_at', 'owner', 'metadata'}
                        model_field_names = {f.name for f in model._meta.get_fields() if not getattr(f, 'auto_created', False)}
                        valid_fields = [f for f in fieldset_fields if f in model_field_names and f not in excluded_fields]
                        if valid_fields:
                            from django.forms import modelform_factory
                            DynamicForm = modelform_factory(model, fields=valid_fields)
                            form_data = serialize_form_for_react(DynamicForm, user=request.user, model_name=model_name_lower)
                            widget_to_type = {
                                'TextInput': 'text',
                                'Textarea': 'textarea',
                                'Select': 'select',
                                'Checkbox': 'checkbox',
                                'DateInput': 'date',
                                'NumberInput': 'number',
                                'EmailInput': 'email',
                            }
                            for field_name in valid_fields:
                                if field_name in form_data:
                                    config = form_data[field_name]
                                    field_info = {
                                        'name': field_name,
                                        'label': config.get('label', field_name.replace('_', ' ').title()),
                                        'type': widget_to_type.get(config.get('widget', 'TextInput'), 'text'),
                                        'required': config.get('required', False),
                                    }
                                    if 'choices' in config:
                                        field_info['choices'] = config['choices']
                                    if 'help_text' in config:
                                        field_info['help_text'] = config['help_text']
                                    form_fields.append(field_info)
                    if not form_fields:
                        form_fields = [
                            {'name': 'name', 'label': 'Name', 'type': 'text', 'required': True}
                        ]
                        if hasattr(model, 'description'):
                            form_fields.append({'name': 'description', 'label': 'Description', 'type': 'textarea', 'required': False})
                return JsonResponse({
                    'form_fields': form_fields,
                    'model_name': model_name
                })
            field_perms, has_field_config, _view_all_fields = get_user_field_permissions(request.user, model_name_lower, settings.APP_METADATA_SETTINGS)
            if has_field_config:
                forbidden_fields = []
                for field_name in request.POST.keys():
                    if field_name in ['csrfmiddlewaretoken', 'metadata']:
                        continue
                    if field_name not in field_perms:
                        forbidden_fields.append(field_name)
                    elif not field_perms[field_name].get('editable', True):
                        forbidden_fields.append(field_name)
                if forbidden_fields:
                    return JsonResponse({
                        'success': False,
                        'error': f'You do not have permission to set the following fields: {", ".join(forbidden_fields)}'
                    }, status=403)
            form_class = getattr(metadata_class, 'form', None)
            if not form_class:
                try:
                    forms_module = __import__(f'{model._meta.app_label}.forms', fromlist=[f'{model_name}Form'])
                    form_class = getattr(forms_module, f'{model_name}Form', None)
                except (ImportError, AttributeError):
                    pass
            if form_class:
                post_data = request.POST.copy()
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"CREATE VIEW DEBUG - POST data received: {dict(post_data)}")
                logger.error(f"CREATE VIEW DEBUG - Form class: {form_class.__name__}")
                if hasattr(form_class, 'metadata_fields'):
                    logger.error(f"CREATE VIEW DEBUG - Form has metadata_fields: {form_class.metadata_fields}")
                    if 'metadata' in post_data and post_data['metadata'] == '[object Object]':
                        del post_data['metadata']
                        logger.error("CREATE VIEW DEBUG - Removed corrupted metadata field '[object Object]'")
                    if 'metadata' not in post_data:
                        import json
                        post_data['metadata'] = json.dumps({})
                        logger.error(f"CREATE VIEW DEBUG - Added empty metadata to POST: {post_data['metadata']}")
                try:
                    form = form_class(post_data, user=request.user)
                except TypeError:
                    form = form_class(post_data)
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
                obj = model()
                try:
                    model._meta.get_field('owner')
                    obj.owner = request.user
                except FieldDoesNotExist:
                    pass
                for field_name, value in request.POST.items():
                    if field_name not in ['id', 'owner', 'created_at', 'updated_at', 'csrfmiddlewaretoken']:
                        _set_model_field_value(obj, field_name, value, model)
                try:
                    obj.save()
                    return JsonResponse({
                        'success': True,
                        'message': f'{model_name} created successfully',
                        'id': str(obj.id) if hasattr(obj, 'id') else None
                    })
                except Exception as e:
                    return JsonResponse({'success': False, 'error': str(e)}, status=400)
        create_view.__name__ = f'{model.__name__.lower()}_create'
        return create_view
    @staticmethod
    def create_update_view(model, metadata_class):
        @login_required
        @require_http_methods(["POST"])
        def update_view(request, **kwargs):
            model_name = model.__name__
            model_name_lower = camel_to_snake(model_name)
            id_param = f'{model_name_lower}_id'
            app_label = model._meta.app_label
            permission = f'{app_label}.change_{model_name_lower}'
            if not request.user.is_superuser:
                django_granted = request.user.has_perm(permission)
                groups_granted = check_group_permission(request.user, model_name_lower, settings.APP_METADATA_SETTINGS)
                profiles_granted = check_profile_permission(request.user, model_name_lower, 'allow_edit', settings.APP_METADATA_SETTINGS)
                if not (django_granted or groups_granted or profiles_granted):
                    raise Http404()
            object_id = kwargs.get(id_param)
            if not object_id:
                return JsonResponse({'error': f'No {model_name} ID provided'}, status=400)
            try:
                queryset = _get_user_queryset(model, request.user)
                obj = queryset.get(id=object_id)
            except model.DoesNotExist:
                return JsonResponse({'error': f'{model_name} not found'}, status=404)
            field_perms, has_field_config, _view_all_fields = get_user_field_permissions(request.user, model_name_lower, settings.APP_METADATA_SETTINGS)
            if has_field_config:
                forbidden_fields = []
                for field_name in request.POST.keys():
                    if field_name in ['csrfmiddlewaretoken', 'metadata']:
                        continue
                    if field_name not in field_perms:
                        forbidden_fields.append(field_name)
                    elif not field_perms[field_name].get('editable', True):
                        forbidden_fields.append(field_name)
                if forbidden_fields:
                    return JsonResponse({
                        'success': False,
                        'error': f'You do not have permission to edit the following fields: {", ".join(forbidden_fields)}'
                    }, status=403)
            form_class = getattr(metadata_class, 'form', None)
            if not form_class:
                try:
                    forms_module = __import__(f'{model._meta.app_label}.forms', fromlist=[f'{model_name}Form'])
                    form_class = getattr(forms_module, f'{model_name}Form', None)
                except (ImportError, AttributeError):
                    pass
            if form_class:
                post_data = request.POST.copy()
                if hasattr(form_class, 'metadata_fields'):
                    if 'metadata' in post_data and post_data['metadata'] == '[object Object]':
                        del post_data['metadata']
                    if 'metadata' not in post_data and hasattr(obj, 'metadata'):
                        current_metadata = obj.metadata if obj.metadata else {}
                        post_data['metadata'] = json.dumps(current_metadata)
                form = form_class(post_data, instance=obj)
                if form.is_valid():
                    form.save()
                    return JsonResponse({'success': True, 'message': f'{model_name} updated successfully'})
                else:
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
                for field_name, value in request.POST.items():
                    if field_name not in ['id', 'owner', 'created_at', 'updated_at', 'csrfmiddlewaretoken']:
                        _set_model_field_value(obj, field_name, value, model)
                try:
                    obj.save()
                    return JsonResponse({'success': True, 'message': f'{model_name} updated successfully'})
                except Exception as e:
                    return JsonResponse({'success': False, 'error': str(e)}, status=400)
        update_view.__name__ = f'{model.__name__.lower()}_update'
        return update_view
    def create_inline_update_view(self, model, metadata_class):
        @login_required
        @require_http_methods(["POST"])
        def inline_update_view(request, **kwargs):
            import json
            import logging
            logger = logging.getLogger(__name__)
            model_name = model.__name__
            model_name_lower = camel_to_snake(model_name)
            id_param = f'{model_name_lower}_id'
            inline_model_name = kwargs.get('inline_model')
            object_id = kwargs.get(id_param)
            if not object_id:
                return JsonResponse({'error': f'No {model_name} ID provided'}, status=400)
            if not inline_model_name:
                return JsonResponse({'error': 'No inline model specified'}, status=400)
            try:
                queryset = _get_user_queryset(model, request.user)
                obj = queryset.get(id=object_id)
            except model.DoesNotExist:
                return JsonResponse({'error': f'{model_name} not found'}, status=404)
            try:
                data = json.loads(request.body)
                add_ids = data.get('add', [])
                remove_ids = data.get('remove', [])
            except (json.JSONDecodeError, KeyError) as e:
                return JsonResponse({'error': f'Invalid request data: {str(e)}'}, status=400)
            inline_class = None
            if hasattr(metadata_class, 'inlines') and metadata_class.inlines:
                for inline in metadata_class.inlines:
                    if inline.model.__name__.lower() == inline_model_name.lower():
                        inline_class = inline
                        break
            if not inline_class:
                return JsonResponse({'error': f'Inline model {inline_model_name} not found'}, status=404)
            inline_model = inline_class.model
            is_through_model = False
            parent_field = None
            related_field = None
            m2m_field = None
            for field in model._meta.many_to_many:
                if field.remote_field.through == inline_model:
                    m2m_field = field.name
                    is_through_model = True
                    for through_field in inline_model._meta.fields:
                        if through_field.related_model == model:
                            parent_field = through_field.name
                        elif through_field.related_model and through_field.related_model != model:
                            related_field = through_field.name
                    break
            if not is_through_model:
                for field in inline_model._meta.fields:
                    if field.related_model == model:
                        parent_field = field.name
                        break
            if not parent_field and not m2m_field:
                return JsonResponse({'error': 'Could not determine relationship type'}, status=400)
            try:
                if m2m_field:
                    m2m_manager = getattr(obj, m2m_field)
                    from uuid import UUID
                    if add_ids:
                        uuid_add_ids = []
                        for id_str in add_ids:
                            try:
                                uuid_add_ids.append(UUID(id_str))
                            except (ValueError, TypeError):
                                uuid_add_ids.append(id_str)
                        m2m_manager.add(*uuid_add_ids)
                    if remove_ids:
                        uuid_remove_ids = []
                        for id_str in remove_ids:
                            try:
                                uuid_remove_ids.append(UUID(id_str))
                            except (ValueError, TypeError):
                                uuid_remove_ids.append(id_str)
                        m2m_manager.remove(*uuid_remove_ids)
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
                else:
                    return JsonResponse({'error': 'Direct FK relationship updates not yet implemented'}, status=400)
            except Exception as e:
                logger.error(f"Error updating inline {inline_model_name}: {str(e)}")
                return JsonResponse({'error': f'Failed to update: {str(e)}'}, status=500)
        inline_update_view.__name__ = f'{model.__name__.lower()}_inline_update'
        return inline_update_view
    def create_available_items_view(self, model, metadata_class):
        @login_required
        def available_items_view(request, **kwargs):
            import json
            model_name = model.__name__
            model_name_lower = camel_to_snake(model_name)
            id_param = f'{model_name_lower}_id'
            inline_type = kwargs.get('inline_type')
            object_id = kwargs.get(id_param)
            if not object_id:
                return JsonResponse({'error': f'No {model_name} ID provided'}, status=400)
            try:
                queryset = _get_user_queryset(model, request.user)
                obj = queryset.get(id=object_id)
            except model.DoesNotExist:
                return JsonResponse({'error': f'{model_name} not found'}, status=404)
            m2m_field = None
            related_model = None
            for field in model._meta.many_to_many:
                field_name = field.name
                if field_name == inline_type or field_name == inline_type.rstrip('s'):
                    m2m_field = field
                    related_model = field.related_model
                    break
            if m2m_field and related_model:
                m2m_manager = getattr(obj, m2m_field.name)
                current_items = m2m_manager.all()
                current_item_ids = [item.id for item in current_items]
                all_items = related_model.objects.exclude(id__in=current_item_ids)
                items = []
                for item in all_items:
                    item_data = {
                        'id': str(item.id),
                        'name': str(item),
                    }
                    if hasattr(item, 'user') and hasattr(item.user, 'email'):
                        item_data['email'] = item.user.email
                    elif hasattr(item, 'email'):
                        item_data['email'] = item.email
                    if hasattr(item, 'description'):
                        item_data['description'] = item.description
                    items.append(item_data)
                return JsonResponse({'items': items})
            return JsonResponse({'items': []})
        available_items_view.__name__ = f'{model.__name__.lower()}_available_items'
        return available_items_view
    @staticmethod
    def create_delete_view(model, metadata_class):
        @login_required
        @require_http_methods(["POST"])
        def delete_view(request, **kwargs):
            model_name = model.__name__
            model_name_lower = camel_to_snake(model_name)
            id_param = f'{model_name_lower}_id'
            app_label = model._meta.app_label
            permission = f'{app_label}.delete_{model_name_lower}'
            if not request.user.is_superuser:
                django_granted = request.user.has_perm(permission)
                groups_granted = check_group_permission(request.user, model_name_lower, settings.APP_METADATA_SETTINGS)
                profiles_granted = check_profile_permission(request.user, model_name_lower, 'allow_delete', settings.APP_METADATA_SETTINGS)
                if not (django_granted or groups_granted or profiles_granted):
                    raise Http404()
            object_id = kwargs.get(id_param)
            if not object_id:
                return JsonResponse({'error': f'No {model_name} ID provided'}, status=400)
            try:
                queryset = _get_user_queryset(model, request.user)
                obj = queryset.get(id=object_id)
            except model.DoesNotExist:
                return JsonResponse({'error': f'{model_name} not found'}, status=404)
            try:
                obj_name = getattr(obj, 'name', str(obj))
                obj.delete()
                return JsonResponse({
                    'success': True,
                    'message': f'{model_name} "{obj_name}" deleted successfully',
                    'redirect_url': f'/m/{model_name_lower}/list'
                })
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Error deleting {model_name} {object_id}: {str(e)}")
                return JsonResponse({
                    'success': False,
                    'error': f'Unable to delete {model_name}. It may have dependent records.'
                }, status=400)
        delete_view.__name__ = f'{model.__name__.lower()}_delete'
        return delete_view


class LegacyRedirectView:
    def __init__(self, app_name, model_name, pattern_type):
        self.app_name = app_name
        self.model_name = model_name
        self.pattern_type = pattern_type
    @classmethod
    def as_view(cls, **initkwargs):
        def view(request, **kwargs):
            from django.http import HttpResponseRedirect
            app_name = initkwargs.get('app_name')
            model_name = initkwargs.get('model_name')
            pattern_type = initkwargs.get('pattern_type')
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
                new_url = f'/app/{app_name}/m/{model_name}/list'
            if request.GET:
                from urllib.parse import urlencode
                query_string = urlencode(request.GET)
                new_url = f'{new_url}?{query_string}'
            return HttpResponseRedirect(new_url)
        return view
