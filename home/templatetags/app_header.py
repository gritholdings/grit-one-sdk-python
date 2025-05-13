from django import template
from home.views import _get_platform_url

register = template.Library()


@register.inclusion_tag('partials/app_header.html', takes_context=True)
def app_header(context):
    request = context.get('request')
    is_authenticated = request.user.is_authenticated if request else False
    user_email = request.user.email if request and request.user.is_authenticated else None
    platform_url = _get_platform_url(request)
    context = {
        'platform_url': platform_url,
        'is_authenticated': is_authenticated,
        'user_email': user_email,
    }
    return context