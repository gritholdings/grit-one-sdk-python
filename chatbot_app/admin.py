from django.contrib import admin
from .models import Prompt

class PromptAdmin(admin.ModelAdmin):
    list_display = ('name', 'status', 'internal_note')
    list_filter = ('status',)
    search_fields = ('name', 'internal_note')

admin.site.register(Prompt, PromptAdmin)