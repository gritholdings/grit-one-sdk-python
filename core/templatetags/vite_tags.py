import json
import os
from django import template
from django.conf import settings
from django.utils.safestring import mark_safe
from django.templatetags.static import static

register = template.Library()

@register.simple_tag
def vite_assets():
    """Include Vite assets in production or development"""
    # Check if Vite dev server is running (development mode with hot reload)
    vite_dev_mode = os.environ.get('DEVELOPMENT_MODE') == 'true' or (
        settings.DEBUG and os.path.exists(os.path.join(settings.BASE_DIR, 'frontend', 'vite.pid'))
    )
    
    if vite_dev_mode:
        # In development with Vite dev server, use the dev server URL
        vite_server = 'http://localhost:5173'
        tags = [
            # React Refresh preamble must come first
            f'<script type="module">',
            f'import RefreshRuntime from "{vite_server}/@react-refresh"',
            f'RefreshRuntime.injectIntoGlobalHook(window)',
            f'window.$RefreshReg$ = () => {{}}',
            f'window.$RefreshSig$ = () => (type) => type',
            f'window.__vite_plugin_react_preamble_installed__ = true',
            f'</script>',
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
    
    with open(manifest_path, 'r') as f:
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
