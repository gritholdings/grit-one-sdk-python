from django.apps import AppConfig


class SalesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'grit.sales'
    label = 'core_sales'
    verbose_name = 'Sales'