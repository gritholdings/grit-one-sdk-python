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
