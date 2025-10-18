import re
from django.shortcuts import redirect
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.urls import resolve, Resolver404
from core.metadata import metadata
from core.utils.permissions import check_group_permission, check_profile_visibility
from core.utils.case_conversion import camel_to_snake
from app import settings


def custom_csrf_failure_view(request, reason=""):
    """
    Custom view for handling CSRF failures.
    Clears the session (or logs out the user) before redirecting
    to a safe page, like the login page or a 'csrf-error' page.
    """
    # Completely flush the session
    if request.session:
        request.session.flush()

    # Log out the user (if they are authenticated)
    logout(request)

    return redirect("login")


@login_required
def app_view(request):
    """
    Smart landing page that redirects authenticated users to their first accessible URL.

    Iterates through APP_METADATA_SETTINGS to find the first tab the user can access,
    checking both model-based URLs (using ownership) and custom URLs (using URL resolution).

    Returns:
        Redirect to first accessible URL, or profile page if none found.
    """
    # Get APP_METADATA_SETTINGS
    app_metadata_settings = getattr(settings, 'APP_METADATA_SETTINGS', {})
    apps = app_metadata_settings.get('APPS', {})
    models_config = app_metadata_settings.get('MODELS', {})
    tabs_config = app_metadata_settings.get('TABS', {})

    # Iterate through all apps and their tabs
    for app_key, app_config in apps.items():
        tabs = app_config.get('tabs', [])

        for tab_key in tabs:
            # Determine the URL for this tab
            # First check if it's a model (models have list URLs at /m/{ModelName}/list)
            if tab_key in models_config:
                # Convert snake_case to PascalCase for model name
                model_name = ''.join(word.capitalize() for word in tab_key.split('_'))
                url = f'/m/{model_name}/list'
            # Then check if it's a custom tab with a URL
            elif tab_key in tabs_config:
                url_name = tabs_config[tab_key].get('url_name', '')
                if url_name:
                    # For now, we'll construct the URL based on common patterns
                    # In a real implementation, you might want to use reverse() here
                    # But since we're checking accessibility via resolution, we need the path
                    url = f'/{url_name}/'
                else:
                    continue
            else:
                # Tab not found in either models or tabs config
                continue

            # Check if user has access to this URL
            if _check_url_access(request.user, url):
                return redirect(url)

    # No accessible URLs found - redirect to profile as default
    return redirect("profile")


def _check_url_access(user, url):
    """
    Check if a user has access to a given URL.

    Args:
        user: Django User object
        url: URL string to check

    Returns:
        Boolean indicating if user has access
    """
    # Pattern 1: Model URLs (/m/{ModelName}/list)
    # Supports multi-word model names like CourseWork, AgentConfig, etc.
    model_url_pattern = r'^/m/([A-Z][A-Za-z0-9]*)/list/?$'
    match = re.match(model_url_pattern, url)

    if match:
        model_name = match.group(1)
        return _check_model_access(user, model_name)

    # Pattern 2: Custom URLs (everything else)
    return _check_custom_url_access(user, url)


def _check_model_access(user, model_name):
    """
    Check if user has access to a model.

    Args:
        user: User object
        model_name: Name of the model to check (e.g., 'Agent')

    Returns:
        Boolean indicating if user has access to the model
    """
    # Get all registered models
    registered_models = metadata.get_registered_models()

    # Find the model class by name
    model_class = None
    for registered_model in registered_models.keys():
        if registered_model.__name__ == model_name:
            model_class = registered_model
            break

    if not model_class:
        # Model not found in registry
        return False

    # Check if user has group permission to access this model
    # Convert PascalCase model name to snake_case for permission check
    # e.g., 'CourseWork' -> 'course_work'
    model_name_snake = camel_to_snake(model_name)

    # Get APP_METADATA_SETTINGS for permission checks
    app_metadata_settings = getattr(settings, 'APP_METADATA_SETTINGS', {})

    # Check permissions using OR logic: groups OR profiles
    return (
        check_group_permission(user, model_name_snake, app_metadata_settings) or
        check_profile_visibility(user, model_name_snake, app_metadata_settings)
    )


def _check_custom_url_access(user, url):
    """
    Check if a custom URL is accessible (exists and user has permission).

    Args:
        user: Django User object
        url: URL string to check

    Returns:
        Boolean indicating if URL is accessible
    """
    # First check if URL can be resolved
    try:
        # Try to resolve the URL as-is
        resolve(url)
    except Resolver404:
        # Try adding trailing slash if not present (Django's APPEND_SLASH behavior)
        if not url.endswith('/'):
            try:
                resolve(url + '/')
            except (Resolver404, Exception):
                return False
        else:
            return False
    except Exception:
        # Other resolution errors
        return False

    # URL exists - now check if user has group permission to access it
    # We need to find which tab this URL corresponds to
    app_metadata_settings = getattr(settings, 'APP_METADATA_SETTINGS', {})
    tabs_config = app_metadata_settings.get('TABS', {})

    # Find the tab_key for this URL by matching url_name
    # Extract the url_name from the URL (e.g., '/tools/' -> 'tools')
    url_stripped = url.strip('/')

    tab_key = None
    for key, tab_config in tabs_config.items():
        url_name = tab_config.get('url_name', '')
        if url_name == url_stripped or f'/{url_name}/' == url or url_name == url:
            tab_key = key
            break

    # If we found a matching tab, check permissions using OR logic: groups OR profiles
    if tab_key:
        return (
            check_group_permission(user, tab_key, app_metadata_settings) or
            check_profile_visibility(user, tab_key, app_metadata_settings)
        )

    # No matching tab found - for safety, deny access
    return False