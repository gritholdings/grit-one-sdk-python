"""
Django settings for core project.
"""

import json
import os
from pathlib import Path
from app.settings import DOMAIN_NAME, AWS_RDS_ENDPOINT
from .utils.env_config import load_credential, get_django_env

# Basics

## Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

## Load the credentials.json file
with open(os.path.join(BASE_DIR, 'credentials.json')) as f:
    credentials = json.load(f)

DJANGO_ENV = get_django_env()

## Set the environment variable from the credentials file
if 'OPENAI_API_KEY' in credentials:
    os.environ['OPENAI_API_KEY'] = credentials['OPENAI_API_KEY']

## Assign the secret key from the JSON file
SECRET_KEY = credentials['SECRET_KEY']

ALLOWED_HOSTS = [".awsapprunner.com", "." + DOMAIN_NAME, "127.0.0.1"]


# Application definition

INSTALLED_APPS = [
    'daphne',
    'django.contrib.admin',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'corsheaders',
    'customauth.apps.CustomauthConfig',
    'django.contrib.auth',
    'rest_framework',
    'adrf',
    'chatbot_app',
    'home',
    'core',
    'core_agent.apps.AgentsConfig',
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

ROOT_URLCONF = 'core.urls'

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
            ],
        },
    },
]

WSGI_APPLICATION = 'core.wsgi.application'
ASGI_APPLICATION = 'core.asgi.application'


# Database is AWS RDS Aurora PostgreSQL
with open(os.getcwd() + '/credentials.json') as f:
    credentials = json.load(f)
    DATABASE_PASSWORD = credentials['DATABASE_PASSWORD']

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

# Authentication

## User Authentication
AUTH_USER_MODEL = 'customauth.CustomUser'

AUTHENTICATION_BACKENDS = [
    'customauth.backends.EmailBackend',
    'django.contrib.auth.backends.ModelBackend'
]

LOGIN_URL = '/auth/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/'


## Password validation
## https://docs.djangoproject.com/en/5.0/ref/settings/#auth-password-validators
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

## REST Framework
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

## CORS
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

### Add CORS_EXPOSE_HEADERS to ensure CSRF token is exposed
CORS_EXPOSE_HEADERS = ['Content-Type', 'X-CSRFToken']

### Configure CSRF settings
CSRF_COOKIE_SECURE = False  # For HTTPS
CSRF_COOKIE_SAMESITE = 'Lax'  # Or 'None' if you need cross-site requests
CSRF_COOKIE_DOMAIN = "." + DOMAIN_NAME  # Include subdomain
CSRF_USE_SESSIONS = False  # Store CSRF token in cookie instead of session
CSRF_COOKIE_HTTPONLY = False  # Allow JavaScript access to CSRF token
CSRF_FAILURE_VIEW = "core.views.custom_csrf_failure_view"

# Email Service
if DJANGO_ENV in ['TEST', 'DEV']:
    # Use locmem backend for tests and local development to prevent sending real emails
    EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
else:
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
    EMAIL_HOST = 'email-smtp.us-east-1.amazonaws.com'
    EMAIL_PORT = 587
    EMAIL_USE_TLS = True
    EMAIL_HOST_USER = load_credential("AWS_SES_SMTP_USERNAME")
    EMAIL_HOST_PASSWORD = load_credential("AWS_SES_SMTP_PASSWORD")
DEFAULT_FROM_EMAIL = 'support@' + DOMAIN_NAME

# Internationalization
# https://docs.djangoproject.com/en/5.0/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.0/howto/static-files/

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

# Default primary key field type
# https://docs.djangoproject.com/en/5.0/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Use environment variables
if DJANGO_ENV == 'PROD' or DJANGO_ENV == 'STAGING':
    DEBUG = False
    if DJANGO_ENV == 'STAGING':
        # The following settings enable printing of the exception traceback in the browser
        DEBUG_PROPAGATE_EXCEPTIONS = True
        from django.views.debug import technical_500_response
        import sys
        def custom_server_error(request):
            # Capture the exception info; note that this works if an exception is active.
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

# Import additional settings that override the default settings
import app.settings as app_settings

INSTALLED_APPS += app_settings.ADDITIONAL_INSTALLED_APPS