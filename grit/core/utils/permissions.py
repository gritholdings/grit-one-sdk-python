from typing import Dict, List, Set, Literal, cast
from copy import deepcopy
from django.http import Http404
from grit.core.types import AppMetadataSettingsTypedDict


def _filter_apps_by_visibility(
    settings: AppMetadataSettingsTypedDict,
    visible_apps: set,
    visible_tabs: set
) -> AppMetadataSettingsTypedDict:
    filtered = deepcopy(settings)
    filtered_apps = {}
    for app_key, app_config in settings.get('APPS', {}).items():
        if app_key in visible_apps:
            original_tabs = app_config.get('tabs', [])
            filtered_tabs = [tab for tab in original_tabs if tab in visible_tabs]
            if filtered_tabs:
                app_config_copy = deepcopy(app_config)
                app_config_copy['tabs'] = filtered_tabs
                filtered_apps[app_key] = app_config_copy
    filtered['APPS'] = filtered_apps
    return filtered


def filter_app_metadata_by_user_groups(settings: AppMetadataSettingsTypedDict, user) -> AppMetadataSettingsTypedDict:
    if not settings or 'GROUPS' not in settings:
        filtered = cast(AppMetadataSettingsTypedDict, deepcopy(settings) if settings else {})
        filtered['APPS'] = {}
        return filtered
    if hasattr(user, 'is_superuser') and user.is_superuser:
        return settings
    user_group_names = [g.name for g in user.groups.all()]
    if not user_group_names:
        filtered = deepcopy(settings)
        filtered['APPS'] = {}
        return filtered
    visible_apps: Set[str] = set()
    visible_tabs: Set[str] = set()
    groups_config = settings.get('GROUPS', {})
    for group_name in user_group_names:
        group_config = groups_config.get(group_name, {})
        app_visibilities = group_config.get('app_visibilities', {})
        for app_key, visibility in app_visibilities.items():
            if visibility.get('visible'):
                visible_apps.add(app_key)
        tab_visibilities = group_config.get('tab_visibilities', {})
        for tab_key, visibility in tab_visibilities.items():
            if visibility.get('visibility') == 'visible':
                visible_tabs.add(tab_key)
    return _filter_apps_by_visibility(settings, visible_apps, visible_tabs)


def filter_app_metadata_by_user_profile(settings: AppMetadataSettingsTypedDict, user) -> AppMetadataSettingsTypedDict:
    if not settings or 'PROFILES' not in settings:
        return settings
    if hasattr(user, 'is_superuser') and user.is_superuser:
        return settings
    if not hasattr(user, 'profile') or not user.profile:
        return settings
    profile = user.profile
    profile_name = profile.name if hasattr(profile, 'name') else None
    if not profile_name:
        return settings
    profiles_config = settings.get('PROFILES', {})
    profile_config = profiles_config.get(profile_name, {})
    if 'app_visibilities' not in profile_config and 'tab_visibilities' not in profile_config:
        return settings
    visible_apps: Set[str] = set()
    visible_tabs: Set[str] = set()
    app_visibilities = profile_config.get('app_visibilities', {})
    for app_key, visibility in app_visibilities.items():
        if visibility.get('visible'):
            visible_apps.add(app_key)
    tab_visibilities = profile_config.get('tab_visibilities', {})
    for tab_key, visibility in tab_visibilities.items():
        if visibility.get('visibility') == 'visible':
            visible_tabs.add(tab_key)
    return _filter_apps_by_visibility(settings, visible_apps, visible_tabs)


def merge_filtered_settings(group_filtered: AppMetadataSettingsTypedDict, profile_filtered: AppMetadataSettingsTypedDict, original: AppMetadataSettingsTypedDict) -> AppMetadataSettingsTypedDict:
    merged = deepcopy(original)
    visible_apps: Set[str] = set()
    visible_tabs: Set[str] = set()
    for app_key in group_filtered.get('APPS', {}).keys():
        visible_apps.add(app_key)
        for tab in group_filtered['APPS'][app_key].get('tabs', []):
            visible_tabs.add(tab)
    for app_key in profile_filtered.get('APPS', {}).keys():
        visible_apps.add(app_key)
        for tab in profile_filtered['APPS'][app_key].get('tabs', []):
            visible_tabs.add(tab)
    merged_apps = {}
    for app_key in original.get('APPS', {}).keys():
        if app_key in visible_apps:
            app_config = deepcopy(original['APPS'][app_key])
            original_tabs = app_config.get('tabs', [])
            app_visible_tabs = [tab for tab in original_tabs if tab in visible_tabs]
            if app_visible_tabs:
                app_config['tabs'] = app_visible_tabs
                merged_apps[app_key] = app_config
    merged['APPS'] = merged_apps
    return merged


def check_group_permission(
    user,
    model_name: str,
    settings: AppMetadataSettingsTypedDict
) -> bool:
    if hasattr(user, 'is_superuser') and user.is_superuser:
        return True
    if not settings or 'GROUPS' not in settings:
        return False
    user_group_names = [g.name for g in user.groups.all()]
    if not user_group_names:
        return False
    app_key, tab_key = _find_app_and_tab_for_model(model_name, settings)
    if not app_key or not tab_key:
        return False
    groups_config = settings.get('GROUPS', {})
    for group_name in user_group_names:
        group_config = groups_config.get(group_name, {})
        app_visibilities = group_config.get('app_visibilities', {})
        tab_visibilities = group_config.get('tab_visibilities', {})
        app_visible = app_visibilities.get(app_key, {}).get('visible', False)
        tab_visible = tab_visibilities.get(tab_key, {}).get('visibility') == 'visible'
        if app_visible and tab_visible:
            return True
    return False


def _find_app_and_tab_for_model(model_name_lower: str, app_metadata: AppMetadataSettingsTypedDict) -> tuple:
    tabs_config = app_metadata.get('TABS', {})
    if model_name_lower in tabs_config:
        apps_config = app_metadata.get('APPS', {})
        for app_key, app_config in apps_config.items():
            if model_name_lower in app_config.get('tabs', []):
                return app_key, model_name_lower
    models_config = app_metadata.get('MODELS', {})
    if model_name_lower in models_config:
        apps_config = app_metadata.get('APPS', {})
        for app_key, app_config in apps_config.items():
            if model_name_lower in app_config.get('tabs', []):
                return app_key, model_name_lower
    return None, None


def check_profile_visibility(
    user,
    model_name: str,
    settings: AppMetadataSettingsTypedDict
) -> bool:
    if hasattr(user, 'is_superuser') and user.is_superuser:
        return True
    if not settings or 'PROFILES' not in settings:
        return False
    if not hasattr(user, 'profile') or not user.profile:
        return False
    profile = user.profile
    profile_name = profile.name if hasattr(profile, 'name') else None
    if not profile_name:
        return False
    profiles_config = settings.get('PROFILES', {})
    profile_config = profiles_config.get(profile_name, {})
    if 'app_visibilities' not in profile_config and 'tab_visibilities' not in profile_config:
        return False
    app_key, tab_key = _find_app_and_tab_for_model(model_name, settings)
    if not app_key or not tab_key:
        return False
    app_visibilities = profile_config.get('app_visibilities', {})
    tab_visibilities = profile_config.get('tab_visibilities', {})
    app_visible = app_visibilities.get(app_key, {}).get('visible', False)
    tab_visible = tab_visibilities.get(tab_key, {}).get('visibility') == 'visible'
    if app_visible and tab_visible:
        return True
    return False


def check_profile_permission(
    user,
    model_name: str,
    permission_type: Literal['allow_create', 'allow_read', 'allow_edit', 'allow_delete', 'allow_summarize'],
    settings: AppMetadataSettingsTypedDict
) -> bool:
    if hasattr(user, 'is_superuser') and user.is_superuser:
        return True
    if not settings or 'PROFILES' not in settings:
        return False
    if not hasattr(user, 'profile') or not user.profile:
        return False
    profile = user.profile
    profile_name = profile.name if hasattr(profile, 'name') else None
    if not profile_name:
        return False
    profiles_config = settings.get('PROFILES', {})
    if profile_name not in profiles_config:
        return False
    profile_config = profiles_config[profile_name]
    model_permissions_dict = profile_config.get('model_permissions', {})
    if model_name not in model_permissions_dict:
        return False
    model_permissions = model_permissions_dict[model_name]
    has_permission = model_permissions.get(permission_type, False)
    return has_permission


def get_user_field_permissions(
    user,
    model_name: str,
    settings: AppMetadataSettingsTypedDict
) -> tuple[Dict[str, Dict[str, bool]], bool, bool]:
    if hasattr(user, 'is_superuser') and user.is_superuser:
        return {}, False, False
    if not settings or 'PROFILES' not in settings:
        return {}, False, False
    if not hasattr(user, 'profile') or not user.profile:
        return {}, False, False
    profile = user.profile
    profile_name = profile.name if hasattr(profile, 'name') else None
    if not profile_name:
        return {}, False, False
    profiles_config = settings.get('PROFILES', {})
    profile_config = profiles_config.get(profile_name, {})
    model_permissions = profile_config.get('model_permissions', {})
    model_perms = model_permissions.get(model_name, {})
    view_all_fields = model_perms.get('view_all_fields', False)
    field_permissions_config = profile_config.get('field_permissions', {})
    if not field_permissions_config:
        return {}, False, view_all_fields
    model_prefix = f'{model_name}.'
    field_perms = {}
    for key, perms in field_permissions_config.items():
        if key.startswith(model_prefix):
            field_name = key[len(model_prefix):]
            field_perms[field_name] = {
                'readable': perms.get('readable', True),
                'editable': perms.get('editable', True)
            }
    return field_perms, True, view_all_fields


def check_field_readable(
    user,
    model_name: str,
    field_name: str,
    settings: AppMetadataSettingsTypedDict
) -> bool:
    field_perms, has_config, view_all_fields = get_user_field_permissions(user, model_name, settings)
    if not has_config and not view_all_fields:
        return True
    if field_name in field_perms:
        return field_perms[field_name].get('readable', True)
    if view_all_fields:
        return True
    if has_config:
        return False
    return True


def check_field_editable(
    user,
    model_name: str,
    field_name: str,
    settings: AppMetadataSettingsTypedDict
) -> bool:
    field_perms, has_config, _view_all_fields = get_user_field_permissions(user, model_name, settings)
    if not has_config:
        return True
    if field_name not in field_perms:
        return False
    return field_perms[field_name].get('editable', True)
