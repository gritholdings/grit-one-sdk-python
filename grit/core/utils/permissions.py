"""
Utilities for filtering app metadata based on user permissions.
"""
from typing import Dict, List, Set, Literal, cast
from copy import deepcopy
from django.http import Http404

from grit.core.types import AppMetadataSettingsTypedDict


def _filter_apps_by_visibility(
    settings: AppMetadataSettingsTypedDict,
    visible_apps: set,
    visible_tabs: set
) -> AppMetadataSettingsTypedDict:
    """
    Filter APPS dict to only include visible apps with visible tabs.

    Args:
        settings: The APP_METADATA_SETTINGS dictionary to filter
        visible_apps: Set of app keys that should be visible
        visible_tabs: Set of tab keys that should be visible

    Returns:
        Deep copy of settings with APPS filtered to only visible apps/tabs
    """
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
    """
    Filter APP_METADATA_SETTINGS based on user's group permissions.

    This function applies group-based visibility rules to apps and tabs,
    ensuring users only receive configuration data they're authorized to see.

    Args:
        settings: The APP_METADATA_SETTINGS dictionary with structure:
            {
                'APPS': {app_key: {label, icon, tabs: [tab_keys]}},
                'MODELS': {model_key: {label, icon, ...}},
                'TABS': {tab_key: {label, url_name, icon}},
                'GROUPS': {
                    group_name: {
                        'app_visibility': {app_key: 'visible'|'hidden'},
                        'tab_visibility': {tab_key: 'visible'|'hidden'}
                    }
                }
            }
        user: Django User object with groups.all() method and is_superuser attribute

    Returns:
        Filtered settings dictionary with same structure, containing only
        apps and tabs visible to the user based on their group memberships.
        Superusers bypass filtering and receive all settings.

    Security Note:
        This implements the principle of least privilege - users should only
        receive metadata for resources they can access, not just have them
        hidden client-side.
    """
    # If no settings or no GROUPS config, return empty apps (secure by default)
    if not settings or 'GROUPS' not in settings:
        filtered = cast(AppMetadataSettingsTypedDict, deepcopy(settings) if settings else {})
        filtered['APPS'] = {}
        return filtered

    # Superusers bypass all filtering
    if hasattr(user, 'is_superuser') and user.is_superuser:
        return settings

    # Get user's group names
    user_group_names = [g.name for g in user.groups.all()]

    # If user has no groups, return empty apps (no access)
    if not user_group_names:
        filtered = deepcopy(settings)
        filtered['APPS'] = {}
        return filtered

    # Aggregate visible apps and tabs across all user's groups
    visible_apps: Set[str] = set()
    visible_tabs: Set[str] = set()

    groups_config = settings.get('GROUPS', {})

    for group_name in user_group_names:
        group_config = groups_config.get(group_name, {})

        # Collect visible apps for this group
        app_visibilities = group_config.get('app_visibilities', {})
        for app_key, visibility in app_visibilities.items():
            if visibility.get('visible'):
                visible_apps.add(app_key)

        # Collect visible tabs for this group
        tab_visibilities = group_config.get('tab_visibilities', {})
        for tab_key, visibility in tab_visibilities.items():
            if visibility.get('visibility') == 'visible':
                visible_tabs.add(tab_key)

    return _filter_apps_by_visibility(settings, visible_apps, visible_tabs)


def filter_app_metadata_by_user_profile(settings: AppMetadataSettingsTypedDict, user) -> AppMetadataSettingsTypedDict:
    """
    Filter APP_METADATA_SETTINGS based on user's profile permissions.

    This function applies profile-based visibility rules to apps and tabs,
    ensuring users only receive configuration data they're authorized to see.

    Args:
        settings: The APP_METADATA_SETTINGS dictionary with structure:
            {
                'APPS': {app_key: {label, icon, tabs: [tab_keys]}},
                'MODELS': {model_key: {label, icon, ...}},
                'TABS': {tab_key: {label, url_name, icon}},
                'PROFILES': {
                    profile_name: {
                        'app_visibilities': {app_key: {'visible': bool}},
                        'tab_visibilities': {tab_key: {'visibility': 'visible'|'hidden'}},
                        'model_permissions': {...}
                    }
                }
            }
        user: Django User object with profile relationship and is_superuser attribute

    Returns:
        Filtered settings dictionary with same structure, containing only
        apps and tabs visible to the user based on their profile configuration.
        Superusers bypass filtering and receive all settings.

    Security Note:
        This implements the principle of least privilege - users should only
        receive metadata for resources they can access, not just have them
        hidden client-side.
    """
    # If no settings or no PROFILES config, return original settings
    if not settings or 'PROFILES' not in settings:
        return settings

    # Superusers bypass all filtering
    if hasattr(user, 'is_superuser') and user.is_superuser:
        return settings

    # Check if user has a profile assigned
    if not hasattr(user, 'profile') or not user.profile:
        # No profile assigned - return settings unchanged (allow other permission layers)
        return settings

    # Get the user's profile name
    profile = user.profile
    profile_name = profile.name if hasattr(profile, 'name') else None

    if not profile_name:
        # Profile exists but has no name - return settings unchanged
        return settings

    # Get profile configuration
    profiles_config = settings.get('PROFILES', {})
    profile_config = profiles_config.get(profile_name, {})

    # If profile has no visibility configuration, return original settings
    if 'app_visibilities' not in profile_config and 'tab_visibilities' not in profile_config:
        return settings

    # Aggregate visible apps and tabs from profile
    visible_apps: Set[str] = set()
    visible_tabs: Set[str] = set()

    # Collect visible apps for this profile
    app_visibilities = profile_config.get('app_visibilities', {})
    for app_key, visibility in app_visibilities.items():
        if visibility.get('visible'):
            visible_apps.add(app_key)

    # Collect visible tabs for this profile
    tab_visibilities = profile_config.get('tab_visibilities', {})
    for tab_key, visibility in tab_visibilities.items():
        if visibility.get('visibility') == 'visible':
            visible_tabs.add(tab_key)

    return _filter_apps_by_visibility(settings, visible_apps, visible_tabs)


def merge_filtered_settings(group_filtered: AppMetadataSettingsTypedDict, profile_filtered: AppMetadataSettingsTypedDict, original: AppMetadataSettingsTypedDict) -> AppMetadataSettingsTypedDict:
    """
    Merge visibility-filtered settings from groups and profiles using OR logic.

    If either filter grants access to an app/tab, it should be included in the result.
    This implements the additive OR semantics: access is granted if ANY permission layer allows it.

    Args:
        group_filtered: Settings filtered by user's groups
        profile_filtered: Settings filtered by user's profile
        original: Original unfiltered settings (for reference)

    Returns:
        Merged settings with apps/tabs visible from EITHER groups OR profiles
    """
    # Start with a deep copy of the original structure
    merged = deepcopy(original)

    # Collect all visible apps from both filters
    visible_apps: Set[str] = set()
    visible_tabs: Set[str] = set()

    # Add apps/tabs from group filter
    for app_key in group_filtered.get('APPS', {}).keys():
        visible_apps.add(app_key)
        for tab in group_filtered['APPS'][app_key].get('tabs', []):
            visible_tabs.add(tab)

    # Add apps/tabs from profile filter (OR logic)
    for app_key in profile_filtered.get('APPS', {}).keys():
        visible_apps.add(app_key)
        for tab in profile_filtered['APPS'][app_key].get('tabs', []):
            visible_tabs.add(tab)

    # Build final filtered APPS with merged visibility
    # Iterate over original APPS to preserve the defined order from APP_METADATA_SETTINGS
    merged_apps = {}
    for app_key in original.get('APPS', {}).keys():
        if app_key in visible_apps:
            app_config = deepcopy(original['APPS'][app_key])
            # Filter tabs to only those visible from either source
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
    """
    Check if a user has group-based permission to access a model.

    This function checks if any of the user's groups grants visibility to the
    app and tab containing the specified model.

    Args:
        user: Django User object with groups.all() method and is_superuser attribute
        model_name: The model name (lowercase) to check permissions for (e.g., 'post', 'course')
        settings: The APP_METADATA_SETTINGS dictionary with GROUPS configuration

    Returns:
        True if user has permission via groups, False otherwise

    Security Note:
        - Superusers bypass all permission checks
        - Uses OR logic: if ANY group grants access, permission is granted
        - Returns False (not Http404) to allow other permission checks to proceed
    """
    # Superusers bypass all permission checks
    if hasattr(user, 'is_superuser') and user.is_superuser:
        return True

    # If no GROUPS configuration exists, deny access
    if not settings or 'GROUPS' not in settings:
        return False

    # Get user's group names
    user_group_names = [g.name for g in user.groups.all()]

    # If user has no groups, deny access
    if not user_group_names:
        return False

    # Find which app and tab this model belongs to
    app_key, tab_key = _find_app_and_tab_for_model(model_name, settings)

    if not app_key or not tab_key:
        # Model not in APP_METADATA_SETTINGS - deny access
        return False

    # Check if any of the user's groups grants access to this app and tab
    groups_config = settings.get('GROUPS', {})

    for group_name in user_group_names:
        group_config = groups_config.get(group_name, {})
        app_visibilities = group_config.get('app_visibilities', {})
        tab_visibilities = group_config.get('tab_visibilities', {})

        # Check if this group grants visibility to both the app and tab
        app_visible = app_visibilities.get(app_key, {}).get('visible', False)
        tab_visible = tab_visibilities.get(tab_key, {}).get('visibility') == 'visible'

        if app_visible and tab_visible:
            # This group grants access - return True (OR logic)
            return True

    # No group grants access
    return False


def _find_app_and_tab_for_model(model_name_lower: str, app_metadata: AppMetadataSettingsTypedDict) -> tuple:
    """
    Find which app and tab a model belongs to based on APP_METADATA_SETTINGS.

    Returns: (app_key, tab_key) or (None, None)
    """
    # First check if model_name is directly a tab
    tabs_config = app_metadata.get('TABS', {})
    if model_name_lower in tabs_config:
        # It's a tab, now find which app contains it
        apps_config = app_metadata.get('APPS', {})
        for app_key, app_config in apps_config.items():
            if model_name_lower in app_config.get('tabs', []):
                return app_key, model_name_lower

    # Otherwise, check if model_name is in MODELS and appears in any app's tabs
    models_config = app_metadata.get('MODELS', {})
    if model_name_lower in models_config:
        # Model is configured, find which app has a tab for it
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
    """
    Check if a user has profile-based visibility access to a model.

    This function checks if the user's profile grants visibility to the
    app and tab containing the specified model via app_visibilities and tab_visibilities.

    Args:
        user: Django User object with profile relationship and is_superuser attribute
        model_name: The model name (lowercase) to check visibility for (e.g., 'post', 'course')
        settings: The APP_METADATA_SETTINGS dictionary with PROFILES configuration

    Returns:
        True if user has visibility via profile, False otherwise

    Security Note:
        - Superusers bypass all permission checks
        - Users without profiles return False (to allow other permission checks via OR logic)
        - Returns False instead of raising Http404 to allow OR-based permission checking
    """
    # Superusers bypass all permission checks
    if hasattr(user, 'is_superuser') and user.is_superuser:
        return True

    # If no PROFILES configuration exists, deny access
    if not settings or 'PROFILES' not in settings:
        return False

    # Check if user has a profile assigned
    if not hasattr(user, 'profile') or not user.profile:
        # No profile assigned - deny access
        return False

    # Get the user's profile name
    profile = user.profile
    profile_name = profile.name if hasattr(profile, 'name') else None

    if not profile_name:
        # Profile exists but has no name - deny access
        return False

    # Get profile configuration
    profiles_config = settings.get('PROFILES', {})
    profile_config = profiles_config.get(profile_name, {})

    # If profile has no visibility configuration, deny access
    if 'app_visibilities' not in profile_config and 'tab_visibilities' not in profile_config:
        return False

    # Find which app and tab this model belongs to
    app_key, tab_key = _find_app_and_tab_for_model(model_name, settings)

    if not app_key or not tab_key:
        # Model not in APP_METADATA_SETTINGS - deny access
        return False

    # Check if this profile grants visibility to both the app and tab
    app_visibilities = profile_config.get('app_visibilities', {})
    tab_visibilities = profile_config.get('tab_visibilities', {})

    # Check if this profile grants visibility to both the app and tab
    app_visible = app_visibilities.get(app_key, {}).get('visible', False)
    tab_visible = tab_visibilities.get(tab_key, {}).get('visibility') == 'visible'

    if app_visible and tab_visible:
        # This profile grants access via visibility
        return True

    # Profile does not grant visibility access
    return False


def check_profile_permission(
    user,
    model_name: str,
    permission_type: Literal['allow_create', 'allow_read', 'allow_edit', 'allow_delete'],
    settings: AppMetadataSettingsTypedDict
) -> bool:
    """
    Check if a user has profile-based permission for a specific model operation.

    This function enforces CRUD permissions based on the user's assigned profile
    and the PROFILES configuration in APP_METADATA_SETTINGS.

    Args:
        user: Django User object with profile relationship and is_superuser attribute
        model_name: The model name (lowercase) to check permissions for (e.g., 'post', 'course')
        permission_type: The permission to check ('allow_create', 'allow_read', 'allow_edit', 'allow_delete')
        settings: The APP_METADATA_SETTINGS dictionary with structure:
            {
                'PROFILES': {
                    'profile_name': {
                        'model_permissions': {
                            'model_name': {
                                'allow_create': bool,
                                'allow_read': bool,
                                'allow_edit': bool,
                                'allow_delete': bool
                            }
                        }
                    }
                }
            }

    Returns:
        True if user has permission, False otherwise

    Security Note:
        - Superusers bypass all permission checks
        - Users without profiles return False (to allow other permission checks via OR logic)
        - Returns False instead of raising Http404 to allow OR-based permission checking
    """
    # Superusers bypass all permission checks
    if hasattr(user, 'is_superuser') and user.is_superuser:
        return True

    # If no PROFILES configuration exists, deny access
    if not settings or 'PROFILES' not in settings:
        return False

    # Check if user has a profile assigned
    if not hasattr(user, 'profile') or not user.profile:
        # No profile assigned - deny access (principle of least privilege)
        return False

    # Get the user's profile name
    profile = user.profile
    profile_name = profile.name if hasattr(profile, 'name') else None

    if not profile_name:
        # Profile exists but has no name - deny access
        return False

    # Get the PROFILES configuration
    profiles_config = settings.get('PROFILES', {})

    # Check if the profile exists in configuration
    if profile_name not in profiles_config:
        # Profile not configured - deny access
        return False

    # Get the profile's configuration
    profile_config = profiles_config[profile_name]

    # Get the model_permissions nested dictionary
    model_permissions_dict = profile_config.get('model_permissions', {})

    # Check if this model is configured for this profile
    if model_name not in model_permissions_dict:
        # Model not configured for this profile - deny access
        return False

    # Get the model's permission configuration
    model_permissions = model_permissions_dict[model_name]

    # Check the specific permission (defaults to False if not specified)
    has_permission = model_permissions.get(permission_type, False)

    return has_permission


def get_user_field_permissions(
    user,
    model_name: str,
    settings: AppMetadataSettingsTypedDict
) -> tuple[Dict[str, Dict[str, bool]], bool, bool]:
    """
    Get field-level permissions for a user on a specific model.

    This function retrieves field permissions from the user's profile configuration
    and returns them in a format convenient for enforcement. Superusers bypass all
    restrictions and get full access to all fields.

    Args:
        user: Django User object with profile relationship and is_superuser attribute
        model_name: The model name (lowercase) to check field permissions for (e.g., 'course')
        settings: The APP_METADATA_SETTINGS dictionary with structure:
            {
                'PROFILES': {
                    'profile_name': {
                        'model_permissions': {
                            'model_name': {
                                'view_all_fields': bool  # Optional - grants read access to all fields
                            }
                        },
                        'field_permissions': {
                            'model.field': {
                                'readable': bool,
                                'editable': bool
                            }
                        }
                    }
                }
            }

    Returns:
        Tuple of (field_permissions_dict, has_field_permissions_config, view_all_fields):
        - field_permissions_dict: Dictionary mapping field names to their permissions:
            {
                'field_name': {'readable': bool, 'editable': bool},
                ...
            }
        - has_field_permissions_config: Boolean indicating if profile has ANY field_permissions
            configured. This distinguishes between "no config" vs "config exists but field missing".
        - view_all_fields: Boolean indicating if view_all_fields is enabled for this model.
            When True, all fields are readable by default unless explicitly overridden in
            field_permissions.

    Security Note:
        - Superusers: returns ({}, False, False) - full access to all fields
        - No profile/config: returns ({}, False, False) - full access to all fields
        - Has config but empty for model: returns ({}, True, False) - DENY all fields for this model
        - Has config with fields: returns ({fields}, True, False) - explicit permissions apply
        - view_all_fields=True: returns ({fields}, True/False, True) - all fields readable by default

    Example:
        >>> perms, has_config, view_all = get_user_field_permissions(user, 'course', settings)
        >>> if view_all and 'name' not in perms:
        >>>     # view_all_fields enabled and field not explicitly denied - allow read
        >>> elif has_config and 'name' not in perms:
        >>>     # Field not in whitelist - deny access
        >>> elif perms.get('name', {}).get('readable', True):
        >>>     # Field is readable
    """
    # Superusers bypass all field restrictions
    if hasattr(user, 'is_superuser') and user.is_superuser:
        return {}, False, False

    # If no PROFILES configuration exists, no restrictions
    if not settings or 'PROFILES' not in settings:
        return {}, False, False

    # Check if user has a profile assigned
    if not hasattr(user, 'profile') or not user.profile:
        # No profile assigned - no restrictions (allow other permission layers)
        return {}, False, False

    # Get the user's profile name
    profile = user.profile
    profile_name = profile.name if hasattr(profile, 'name') else None

    if not profile_name:
        # Profile exists but has no name - no restrictions
        return {}, False, False

    # Get profile configuration
    profiles_config = settings.get('PROFILES', {})
    profile_config = profiles_config.get(profile_name, {})

    # Check for view_all_fields in model_permissions
    model_permissions = profile_config.get('model_permissions', {})
    model_perms = model_permissions.get(model_name, {})
    view_all_fields = model_perms.get('view_all_fields', False)

    # Get field_permissions from profile
    field_permissions_config = profile_config.get('field_permissions', {})

    # If view_all_fields is True but no field_permissions, return early with view_all_fields flag
    if not field_permissions_config:
        # No field permissions configured
        # If view_all_fields is True, we still want to signal that
        return {}, False, view_all_fields

    # Profile HAS field_permissions configured - this is important for default behavior
    # Parse field permissions for this specific model
    # Format is 'model.field': {'readable': bool, 'editable': bool}
    model_prefix = f'{model_name}.'
    field_perms = {}

    for key, perms in field_permissions_config.items():
        if key.startswith(model_prefix):
            # Extract field name from 'model.field' format
            field_name = key[len(model_prefix):]
            field_perms[field_name] = {
                'readable': perms.get('readable', True),
                'editable': perms.get('editable', True)
            }

    # Return field permissions, config flag, AND view_all_fields flag
    # This allows callers to distinguish "no config" from "field not in whitelist"
    # and also check if view_all_fields grants default read access
    return field_perms, True, view_all_fields


def check_field_readable(
    user,
    model_name: str,
    field_name: str,
    settings: AppMetadataSettingsTypedDict
) -> bool:
    """
    Check if a user can read a specific field on a model.

    This is a convenience function that wraps get_user_field_permissions()
    for simple boolean checks.

    Args:
        user: Django User object
        model_name: The model name (lowercase) e.g., 'course'
        field_name: The field name e.g., 'description'
        settings: The APP_METADATA_SETTINGS dictionary

    Returns:
        True if user can read the field, False otherwise

        Behavior:
        - Superuser or no field_permissions config: returns True (allow all)
        - view_all_fields=True and field not explicitly denied: returns True
        - Profile has field_permissions but field not listed: returns False (whitelist mode)
        - Field explicitly listed: returns the configured readable value

    Example:
        >>> if check_field_readable(user, 'course', 'name', settings):
        >>>     obj_data['name'] = obj.name
    """
    field_perms, has_config, view_all_fields = get_user_field_permissions(user, model_name, settings)

    # No config and no view_all_fields means no restrictions (superuser or no field_permissions)
    if not has_config and not view_all_fields:
        return True

    # If field is explicitly configured, use that value (overrides view_all_fields)
    if field_name in field_perms:
        return field_perms[field_name].get('readable', True)

    # If view_all_fields is enabled and field not explicitly denied, allow read access
    if view_all_fields:
        return True

    # Config exists but field not in whitelist - deny access (whitelist mode)
    if has_config:
        return False

    return True


def check_field_editable(
    user,
    model_name: str,
    field_name: str,
    settings: AppMetadataSettingsTypedDict
) -> bool:
    """
    Check if a user can edit a specific field on a model.

    This is a convenience function that wraps get_user_field_permissions()
    for simple boolean checks.

    Args:
        user: Django User object
        model_name: The model name (lowercase) e.g., 'course'
        field_name: The field name e.g., 'description'
        settings: The APP_METADATA_SETTINGS dictionary

    Returns:
        True if user can edit the field, False otherwise

        Behavior:
        - Superuser or no field_permissions config: returns True (allow all)
        - Profile has field_permissions but field not listed: returns False (whitelist mode)
        - Field explicitly listed: returns the configured editable value

        Note: view_all_fields only affects read access, not edit access.
        Edit permissions still require explicit field_permissions configuration.

    Example:
        >>> if not check_field_editable(user, 'course', 'status', settings):
        >>>     return JsonResponse({'error': 'Cannot edit status field'}, status=403)
    """
    field_perms, has_config, _view_all_fields = get_user_field_permissions(user, model_name, settings)

    # No config means no restrictions (superuser or no field_permissions)
    if not has_config:
        return True

    # Config exists - if field not in whitelist, deny access
    # Note: view_all_fields does NOT grant edit access, only read access
    if field_name not in field_perms:
        return False

    # Return the explicit editable setting
    return field_perms[field_name].get('editable', True)
