import json
import os
import logging
from django import template
from django.conf import settings
from django.utils.safestring import mark_safe
from django.templatetags.static import static

logger = logging.getLogger(__name__)
register = template.Library()


def is_vite_dev_server_running():
    """
    Check if Vite dev server is actually running and healthy.
    Returns True if server is confirmed running, False otherwise.

    This performs a robust check:
    1. Verifies vite.pid file exists
    2. Reads the PID and confirms the process is alive
    3. Falls back gracefully if PID is stale
    """
    pid_file_path = os.path.join(settings.BASE_DIR, 'frontend', 'vite.pid')

    # First check: Does PID file exist?
    if not os.path.exists(pid_file_path):
        return False

    try:
        # Second check: Read PID and verify process is alive
        with open(pid_file_path, 'r', encoding='utf-8') as f:
            pid_str = f.read().strip()

        if not pid_str:
            logger.warning("vite.pid file exists but is empty - removing stale file")
            os.remove(pid_file_path)
            return False

        pid = int(pid_str)

        # Third check: Is the process actually running?
        # os.kill with signal 0 doesn't actually kill, just checks if process exists
        try:
            os.kill(pid, 0)
            # Process exists and we have permission to signal it
            return True
        except OSError:
            # Process doesn't exist - stale PID file
            logger.warning(
                "Vite PID file exists but process %d is not running. "
                "Removing stale vite.pid file. Vite may have crashed.",
                pid
            )
            os.remove(pid_file_path)
            return False

    except (ValueError, IOError) as e:
        logger.error("Error checking Vite dev server status: %s", e)
        # If we can't read/parse the PID file, assume dev server is not running
        return False


@register.simple_tag
def vite_assets():
    """Include Vite assets in production or development"""
    # Check if Vite dev server is running (development mode with hot reload)
    # DJANGO_ENV=PROD should always use production build
    vite_dev_mode = (
        os.environ.get('DJANGO_ENV') != 'PROD' and
        (os.environ.get('DEVELOPMENT_MODE') == 'true' or
         (settings.DEBUG and is_vite_dev_server_running()))
    )
    
    if vite_dev_mode:
        # In development with Vite dev server, use the dev server URL
        vite_server = 'http://localhost:5173'
        tags = [
            # React Refresh preamble must come first
            '<script type="module">',
            f'import RefreshRuntime from "{vite_server}/@react-refresh"',
            'RefreshRuntime.injectIntoGlobalHook(window)',
            'window.$RefreshReg$ = () => {}',
            'window.$RefreshSig$ = () => (type) => type',
            'window.__vite_plugin_react_preamble_installed__ = true',
            '</script>',
            f'<script type="module" src="{vite_server}/@vite/client"></script>',
            f'<script type="module" src="{vite_server}/src/main.tsx"></script>'
        ]
        return mark_safe('\n'.join(tags))
    
    # Production mode or development without Vite dev server
    # Choose manifest path based on DEBUG setting
    if settings.DEBUG:
        # In development, read from source static files
        manifest_path = os.path.join(settings.BASE_DIR, 'home/static/home/dist/manifest.json')
    else:
        # In production, read from collected static files
        manifest_path = os.path.join(settings.STATIC_ROOT, 'home/dist/manifest.json')
    
    if not os.path.exists(manifest_path):
        return ''

    with open(manifest_path, 'r', encoding='utf-8') as f:
        manifest = json.load(f)
    
    # Get the main entry file
    main_file = manifest.get('src/main.tsx', {})
    
    tags = []
    
    # Include CSS if exists
    if 'css' in main_file:
        for css_file in main_file['css']:
            css_url = static(f'home/dist/{css_file}')
            tags.append(f'<link rel="stylesheet" href="{css_url}">')
    
    # Include JS
    if 'file' in main_file:
        js_url = static(f'home/dist/{main_file["file"]}')
        tags.append(f'<script type="module" src="{js_url}"></script>')

    return mark_safe('\n'.join(tags))
