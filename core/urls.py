"""
Core Urls
"""
from django.contrib import admin
from django.urls import path, include
from chatbot_app import views as chatbot_app_views
from chatbot_app import aviews as achatbot_app_views
from home import views as home_views
from rest_framework import routers

router = routers.DefaultRouter()

urlpatterns = [
    path('auth/', include('customauth.urls')),
    path('admin/', admin.site.urls),
    path('api/', include(router.urls)),
    path('api/threads/create', chatbot_app_views.create_thread, name='create_thread'),
    path('api/threads/runs', achatbot_app_views.threads_runs, name='threads_runs'),
    path('api/threads/list', chatbot_app_views.threads_list, name='threads_list'),
    path('api/threads/', chatbot_app_views.thread_detail, name='thread_detail'),
    path('api/files/upload', achatbot_app_views.upload_files, name='upload_files'),
    path('api/models', chatbot_app_views.models_list, name='models_list'),
    path('onboarding/<int:step>/', home_views.onboarding, name='onboarding'),
    path('onboarding/save/', home_views.save_onboarding_progress, name='save_onboarding_progress'),
    path('profile/', home_views.profile, name='profile'),
    path('', include('app.urls')),
]