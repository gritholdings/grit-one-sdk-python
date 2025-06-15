"""
Core Urls
"""
from django.contrib import admin
from django.urls import path, include
from home import views as home_views

urlpatterns = [
    path('auth/', include('customauth.urls')),
    path('admin/', admin.site.urls),
    path('onboarding/<int:step>/', home_views.onboarding, name='onboarding'),
    path('onboarding/save/', home_views.save_onboarding_progress, name='save_onboarding_progress'),
    path('profile/', home_views.profile, name='profile'),
    path('', include('app.urls')),
]