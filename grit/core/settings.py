import os
from pathlib import Path
from app.settings import DOMAIN_NAME, AWS_RDS_ENDPOINT, APP_METADATA_SETTINGS
from .utils.env_config import load_credential, set_environ_credential, get_django_env
from .core_settings import core_settings
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DJANGO_ENV = get_django_env()
set_environ_credential('OPENAI_API_KEY')
set_environ_credential('ANTHROPIC_API_KEY')
SECRET_KEY = load_credential('SECRET_KEY')
ALLOWED_HOSTS = [".awsapprunner.com", "." + DOMAIN_NAME, "127.0.0.1"]
INSTALLED_APPS = [
    'daphne',
    'django.contrib.admin',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'corsheaders',
    'grit.auth.apps.CustomauthConfig',
    'django.contrib.auth',
    'rest_framework',
    'adrf',
    'app.agent',
    'home',
    'grit.core.apps.CoreConfig',
    'grit.agent.apps.AgentsConfig',
    'app'
]
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware'
]
ROOT_URLCONF = 'grit.core.urls'
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'grit.core.context_processors.environment_context',
            ],
        },
    },
]
WSGI_APPLICATION = 'grit.core.wsgi.application'
ASGI_APPLICATION = 'grit.core.asgi.application'
DATABASE_PASSWORD = load_credential('DATABASE_PASSWORD')
if DJANGO_ENV == 'TEST':
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME':'postgres',
            'USER':'postgres',
            'PASSWORD': DATABASE_PASSWORD,
            'HOST':AWS_RDS_ENDPOINT,
            'PORT':'5432'
        }
    }
AUTH_USER_MODEL = 'customauth.CustomUser'
AUTHENTICATION_BACKENDS = [
    'grit.auth.backends.EmailBackend',
    'django.contrib.auth.backends.ModelBackend'
]
LOGIN_URL = '/auth/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/'
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
}
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOWED_ORIGINS = [
    'http://127.0.0.1:3000',
    "https://*.awsapprunner.com",
    "https://platform." + DOMAIN_NAME
]
CSRF_TRUSTED_ORIGINS = [
    "http://127.0.0.1:3000",
    "https://*.awsapprunner.com",
    "https://*." + DOMAIN_NAME
]
CORS_EXPOSE_HEADERS = ['Content-Type', 'X-CSRFToken']
CSRF_COOKIE_SECURE = False
CSRF_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_DOMAIN = "." + DOMAIN_NAME
CSRF_USE_SESSIONS = False
CSRF_COOKIE_HTTPONLY = False
CSRF_FAILURE_VIEW = "grit.core.views.custom_csrf_failure_view"
if DJANGO_ENV in ['TEST', 'DEV']:
    EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
else:
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
    EMAIL_HOST = 'email-smtp.us-east-1.amazonaws.com'
    EMAIL_PORT = 587
    EMAIL_USE_TLS = True
    EMAIL_HOST_USER = load_credential("AWS_SES_SMTP_USERNAME")
    EMAIL_HOST_PASSWORD = load_credential("AWS_SES_SMTP_PASSWORD")
DEFAULT_FROM_EMAIL = 'support@' + DOMAIN_NAME
LANGUAGE_CODE = 'en-us'
TIME_ZONE = core_settings.TIME_ZONE
USE_I18N = True
USE_TZ = True
STATIC_URL = 'static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
if DJANGO_ENV == 'PROD' or DJANGO_ENV == 'STAGING':
    DEBUG = False
    if DJANGO_ENV == 'STAGING':
        DEBUG_PROPAGATE_EXCEPTIONS = True
        from django.views.debug import technical_500_response
        import sys
        def custom_server_error(request):
            return technical_500_response(request, *sys.exc_info())
        handler500 = custom_server_error
        from whitenoise.storage import CompressedManifestStaticFilesStorage
        class NonStrictManifestStaticFilesStorage(CompressedManifestStaticFilesStorage):
            manifest_strict = False
elif DJANGO_ENV == 'DEV':
    DEBUG = True
    CSRF_COOKIE_DOMAIN = None
else:
    DEBUG = True
import app.settings as app_settings
INSTALLED_APPS += app_settings.ADDITIONAL_INSTALLED_APPS
if hasattr(app_settings, 'ADDITIONAL_SETTINGS'):
    globals().update(app_settings.ADDITIONAL_SETTINGS)