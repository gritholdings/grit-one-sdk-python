from django.urls import path
from . import views as core_agent_views


urlpatterns = [
    path('knowledge-base-webhook/', core_agent_views.knowledge_base_webhook, name='knowledge_base_webhook'),
]