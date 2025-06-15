from app import settings as app_settings
from django.utils.module_loading import import_string
from django.urls import path
from chatbot_app import views as chatbot_app_views
from chatbot_app import aviews as achatbot_app_views
from . import views as core_agent_views


# Dynamically import configurable views
threads_runs_aview = import_string(getattr(app_settings, 'THREADS_RUNS_AVIEW', 'chatbot_app.aviews.threads_runs'))
threads_list_view = import_string(getattr(app_settings, 'THREADS_LIST_VIEW', 'chatbot_app.views.threads_list'))
models_list_view = import_string(getattr(app_settings, 'MODELS_LIST_VIEW', 'chatbot_app.views.models_list'))


urlpatterns = [
    path('api/threads/create', chatbot_app_views.create_thread, name='create_thread'),
    path('api/threads/', chatbot_app_views.thread_detail, name='thread_detail'),
    path('api/files/upload', achatbot_app_views.upload_files, name='upload_files'),
    path('api/threads/runs', threads_runs_aview, name='threads_runs'),
    path('api/threads/list', threads_list_view, name='threads_list'),
    path('api/models', models_list_view, name='models_list'),
    path('knowledge-base-webhook/', core_agent_views.knowledge_base_webhook, name='knowledge_base_webhook'),
]