from django.urls import path
from django.utils.module_loading import import_string
from . import views as core_agent_views
from . import aviews as core_agent_aviews
from .settings import agent_settings


urlpatterns = [
    path('chat/', core_agent_views.chat_view, name='agent_chat_new'),
    path('chat/c/<str:thread_id>', core_agent_views.chat_view, name='agent_chat'),
    path('api/threads/create', core_agent_views.create_thread, name='create_thread'),
    path('api/threads/', core_agent_views.thread_detail, name='thread_detail'),
    path('api/files/upload', core_agent_aviews.upload_files, name='upload_files'),
    path('api/threads/runs', import_string(agent_settings.THREADS_RUNS_AVIEW), name='threads_runs'),
    path('api/threads/list', import_string(agent_settings.THREADS_LIST_VIEW), name='threads_list'),
    path('api/models', import_string(agent_settings.MODELS_LIST_VIEW), name='models_list'),
    path('api/default-config', core_agent_views.default_config, name='default_config'),
    path('knowledge-base-webhook/', core_agent_views.knowledge_base_webhook, name='knowledge_base_webhook'),
    path('mcp', core_agent_views.mcp_query, name='mcp_query'),
]