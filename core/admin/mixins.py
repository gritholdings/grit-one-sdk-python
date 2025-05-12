from django.urls import reverse
from django.utils.html import format_html


class ClickableInlineMixin:
    def object_link(self, instance):
        if instance.pk:
            try:
                url = reverse(
                    'admin:%s_%s_change' % (instance._meta.app_label, instance._meta.model_name),
                    args=(instance.pk,),
                )
                return format_html('<a href="{}">{}</a>', url, instance)
            except Exception as e:
                # Fallback for unregistered models
                return str(instance)
        return "(New)"
    
    def has_change_permission(self, request, obj=None):
        return False
    
    def has_add_permission(self, request, obj=None):
        return False