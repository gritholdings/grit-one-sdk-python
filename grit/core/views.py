import re
from django.shortcuts import redirect
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.urls import resolve, Resolver404
from grit.core.metadata import metadata
from grit.core.utils.permissions import check_group_permission, check_profile_visibility
from grit.core.utils.case_conversion import camel_to_snake
from app import settings


def custom_csrf_failure_view(request, reason=""):
    if request.session:
        request.session.flush()
    logout(request)
    return redirect("login")


def _resolve_tab_url(tab_key, app_metadata_settings, app_name=None):
    models_config = app_metadata_settings.get('MODELS', {})
    tabs_config = app_metadata_settings.get('TABS', {})
    if tab_key in models_config:
        if not app_name:
            return None
        return f'/app/{app_name}/m/{tab_key}/list'
    elif tab_key in tabs_config:
        url_name = tabs_config[tab_key].get('url_name', '')
        if url_name:
            return f'/{url_name}/'
    return None


def _find_first_accessible_tab(user, tabs, app_metadata_settings, app_name=None):
    for tab_key in tabs:
        url = _resolve_tab_url(tab_key, app_metadata_settings, app_name)
        if url and _check_url_access(user, url):
            return url
    return None
@login_required


def app_view(request):
    app_metadata_settings = getattr(settings, 'APP_METADATA_SETTINGS', {})
    apps = app_metadata_settings.get('APPS', {})
    for app_key, app_config in apps.items():
        tabs = app_config.get('tabs', [])
        first_accessible_url = _find_first_accessible_tab(request.user, tabs, app_metadata_settings, app_key)
        if first_accessible_url:
            return redirect(first_accessible_url)
    return redirect("profile")
@login_required


def app_specific_view(request, app_name):
    app_metadata_settings = getattr(settings, 'APP_METADATA_SETTINGS', {})
    apps = app_metadata_settings.get('APPS', {})
    if app_name not in apps:
        raise Http404(f"App '{app_name}' not found in APP_METADATA_SETTINGS")
    app_config = apps[app_name]
    tabs = app_config.get('tabs', [])
    first_accessible_url = _find_first_accessible_tab(request.user, tabs, app_metadata_settings, app_name)
    if first_accessible_url:
        return redirect(first_accessible_url)
    return redirect("profile")


def _check_url_access(user, url):
    new_model_url_pattern = r'^/app/([a-z_]+)/m/([a-z_]+)/list/?$'
    match = re.match(new_model_url_pattern, url)
    if match:
        model_name_snake = match.group(2)
        return _check_model_access(user, model_name_snake)
    legacy_model_url_pattern = r'^/m/([A-Z][A-Za-z0-9]*)/list/?$'
    match = re.match(legacy_model_url_pattern, url)
    if match:
        model_name = match.group(1)
        return _check_model_access(user, model_name)
    return _check_custom_url_access(user, url)


def _check_model_access(user, model_name):
    registered_models = metadata.get_registered_models()
    is_snake_case = '_' in model_name or model_name.islower()
    model_class = None
    if is_snake_case:
        model_name_pascal = ''.join(word.capitalize() for word in model_name.split('_'))
        for registered_model in registered_models.keys():
            if registered_model.__name__ == model_name_pascal:
                model_class = registered_model
                break
        model_name_snake = model_name
    else:
        for registered_model in registered_models.keys():
            if registered_model.__name__ == model_name:
                model_class = registered_model
                break
        model_name_snake = camel_to_snake(model_name)
    if not model_class:
        return False
    app_metadata_settings = getattr(settings, 'APP_METADATA_SETTINGS', {})
    return (
        check_group_permission(user, model_name_snake, app_metadata_settings) or
        check_profile_visibility(user, model_name_snake, app_metadata_settings)
    )


def _check_custom_url_access(user, url):
    try:
        resolve(url)
    except Resolver404:
        if not url.endswith('/'):
            try:
                resolve(url + '/')
            except (Resolver404, Exception):
                return False
        else:
            return False
    except Exception:
        return False
    app_metadata_settings = getattr(settings, 'APP_METADATA_SETTINGS', {})
    tabs_config = app_metadata_settings.get('TABS', {})
    url_stripped = url.strip('/')
    tab_key = None
    for key, tab_config in tabs_config.items():
        url_name = tab_config.get('url_name', '')
        if url_name == url_stripped or f'/{url_name}/' == url or url_name == url:
            tab_key = key
            break
    if tab_key:
        return (
            check_group_permission(user, tab_key, app_metadata_settings) or
            check_profile_visibility(user, tab_key, app_metadata_settings)
        )
    return False