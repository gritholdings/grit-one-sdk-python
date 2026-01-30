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
    pid_file_path = os.path.join(settings.BASE_DIR, 'frontend', 'vite.pid')
    if not os.path.exists(pid_file_path):
        return False
    try:
        with open(pid_file_path, 'r', encoding='utf-8') as f:
            pid_str = f.read().strip()
        if not pid_str:
            logger.warning("vite.pid file exists but is empty - removing stale file")
            os.remove(pid_file_path)
            return False
        pid = int(pid_str)
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            logger.warning(
                "Vite PID file exists but process %d is not running. "
                "Removing stale vite.pid file. Vite may have crashed.",
                pid
            )
            os.remove(pid_file_path)
            return False
    except (ValueError, IOError) as e:
        logger.error("Error checking Vite dev server status: %s", e)
        return False
@register.simple_tag


def vite_assets():
    vite_dev_mode = (
        os.environ.get('DJANGO_ENV') != 'PROD' and
        (os.environ.get('DEVELOPMENT_MODE') == 'true' or
         (settings.DEBUG and is_vite_dev_server_running()))
    )
    if vite_dev_mode:
        vite_server = 'http://localhost:5173'
        tags = [
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
    if settings.DEBUG:
        manifest_path = os.path.join(settings.BASE_DIR, 'home/static/home/dist/manifest.json')
    else:
        manifest_path = os.path.join(settings.STATIC_ROOT, 'home/dist/manifest.json')
    if not os.path.exists(manifest_path):
        return ''
    with open(manifest_path, 'r', encoding='utf-8') as f:
        manifest = json.load(f)
    main_file = manifest.get('src/main.tsx', {})
    tags = []
    if 'css' in main_file:
        for css_file in main_file['css']:
            css_url = static(f'home/dist/{css_file}')
            tags.append(f'<link rel="stylesheet" href="{css_url}">')
    if 'file' in main_file:
        js_url = static(f'home/dist/{main_file["file"]}')
        tags.append(f'<script type="module" src="{js_url}"></script>')
    return mark_safe('\n'.join(tags))
