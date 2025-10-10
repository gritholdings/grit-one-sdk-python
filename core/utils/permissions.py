"""
Utilities for filtering app metadata based on user permissions.
"""
from typing import Dict, List, Set, Literal
from copy import deepcopy
from django.http import Http404


def filter_app_metadata_by_user_groups(settings: Dict, user) -> Dict:
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
    # If no settings or no GROUPS config, return original settings
    if not settings or 'GROUPS' not in settings:
        return settings

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
        app_visibility = group_config.get('app_visibility', {})
        for app_key, visibility in app_visibility.items():
            if visibility == 'visible':
                visible_apps.add(app_key)

        # Collect visible tabs for this group
        tab_visibility = group_config.get('tab_visibility', {})
        for tab_key, visibility in tab_visibility.items():
            if visibility == 'visible':
                visible_tabs.add(tab_key)

    # Deep copy to avoid mutating original settings
    filtered = deepcopy(settings)

    # Filter APPS
    filtered_apps = {}
    for app_key, app_config in settings.get('APPS', {}).items():
        # Only include app if it's in visible_apps
        if app_key in visible_apps:
            # Filter the tabs within this app
            original_tabs = app_config.get('tabs', [])
            filtered_tabs = [tab for tab in original_tabs if tab in visible_tabs]

            # Only include app if it has at least one visible tab
            if filtered_tabs:
                app_config_copy = deepcopy(app_config)
                app_config_copy['tabs'] = filtered_tabs
                filtered_apps[app_key] = app_config_copy

    filtered['APPS'] = filtered_apps

    return filtered


def check_group_permission(
    user,
    model_name: str,
    settings: Dict
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
        app_visibility = group_config.get('app_visibility', {})
        tab_visibility = group_config.get('tab_visibility', {})

        # Check if this group grants visibility to both the app and tab
        app_visible = app_visibility.get(app_key) == 'visible'
        tab_visible = tab_visibility.get(tab_key) == 'visible'

        if app_visible and tab_visible:
            # This group grants access - return True (OR logic)
            return True

    # No group grants access
    return False


def _find_app_and_tab_for_model(model_name_lower: str, app_metadata: Dict) -> tuple:
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


def check_profile_permission(
    user,
    model_name: str,
    permission_type: Literal['allow_create', 'allow_read', 'allow_edit', 'allow_delete'],
    settings: Dict
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
                        'model_name': {
                            'allow_create': bool,
                            'allow_read': bool,
                            'allow_edit': bool,
                            'allow_delete': bool
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

    # Check if this model is configured for this profile
    if model_name not in profile_config:
        # Model not configured for this profile - deny access
        return False

    # Get the model's permission configuration
    model_permissions = profile_config[model_name]

    # Check the specific permission (defaults to False if not specified)
    has_permission = model_permissions.get(permission_type, False)

    return has_permission
