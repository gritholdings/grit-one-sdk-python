from django.urls import reverse
from django.utils.html import format_html


class ClickableInlineMixin:
    def object_link(self, instance):
        if instance.pk:
            url = reverse(
                'admin:%s_%s_change' % (instance._meta.app_label, instance._meta.model_name),
                args=(instance.pk,),
            )
            return format_html('<a href="{}">{}</a>', url, instance)
        return "(New)"