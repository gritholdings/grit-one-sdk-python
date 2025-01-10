"""
URL configuration for chatbot project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from chatbot_app import views as chatbot_app_views
from home import views as home_views
from rest_framework import routers

router = routers.DefaultRouter()

urlpatterns = [
    path('', home_views.index, name='index'),
    path('pricing/', home_views.pricing, name='pricing'),
    path('auth/', include('customauth.urls')),
    path('admin/', admin.site.urls),
    path('api/', include(router.urls)),
    path('api/threads/create', chatbot_app_views.create_thread, name='create_thread'),
    path('api/threads/runs', chatbot_app_views.threads_runs, name='threads_runs'),
    path('api/files/upload', chatbot_app_views.upload_files, name='upload_files'),
    path('api/models', chatbot_app_views.models_list, name='models_list'),
    path('onboarding/<int:step>/', home_views.onboarding, name='onboarding'),
    path('onboarding/save/', home_views.save_onboarding_progress, name='save_onboarding_progress'),
    path('about-us/', home_views.about_us, name='about_us'),
    path('terms-and-conditions/', home_views.terms_and_conditions, name='terms-and-conditions'),
    path('profile/', home_views.profile, name='profile'),
    path('payments/', include('core_payments.urls'))
]