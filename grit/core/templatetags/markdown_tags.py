from django.template import Library
from django.template.loader import get_template
from django.utils.safestring import mark_safe
import markdown2
register = Library()
MARKDOWN_EXTRAS = ['fenced-code-blocks', 'tables', 'code-friendly', 'cuddled-lists']
@register.simple_tag


def render_markdown(template_path):
    tmpl = get_template(template_path)
    file_path = tmpl.origin.name
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    html = markdown2.markdown(content, extras=MARKDOWN_EXTRAS)
    return mark_safe(html)
