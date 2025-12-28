from django.apps import AppConfig


class CustomauthConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'grit.auth'
    label = 'customauth'
    verbose_name = 'Users'
