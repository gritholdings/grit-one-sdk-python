"""
Custom context processors for the Grit application.

These processors add variables to the template context for all requests.
"""
from grit.core.utils.env_config import DJANGO_ENV


def environment_context(request):
    """
    Add environment-related variables to the template context.

    Returns:
        dict: Context variables including:
            - IS_PRODUCTION: Boolean indicating if running in production
    """
    return {
        'IS_PRODUCTION': DJANGO_ENV == 'PROD',
    }
