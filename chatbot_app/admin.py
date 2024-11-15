from django.contrib import admin
from .models import Prompt

admin.site.site_header = "Your Company, Inc. Administration"

class PromptAdmin(admin.ModelAdmin):
    list_display = ('name', 'status', 'internal_note')
    list_filter = ('status',)
    search_fields = ('name', 'internal_note')

admin.site.register(Prompt, PromptAdmin)