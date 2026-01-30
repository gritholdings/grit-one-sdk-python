from grit.core.utils.env_config import DJANGO_ENV


def environment_context(request):
    return {
        'IS_PRODUCTION': DJANGO_ENV == 'PROD',
    }
