"""
Core Urls
"""
from django.contrib import admin
from django.urls import path, include
from home import views as home_views
from core import views as core_views
from core.metadata import metadata
from core.metadata.autodiscover import autodiscover
from core.shortcuts import auth_redirect

# Autodiscover metadata registrations from all apps
autodiscover()

urlpatterns = [
    path('auth/', include('customauth.urls')),
    path('admin/', admin.site.urls),
    path('onboarding/<int:step>/', home_views.onboarding, name='onboarding'),
    path('onboarding/save/', home_views.save_onboarding_progress, name='save_onboarding_progress'),
    path('profile/', home_views.profile, name='profile'),
    path('app/', core_views.app_view, name='app'),
    path('', auth_redirect('app', 'home'), name='index'),
    path('', include('app.urls')),
]

# Append auto-generated metadata URLs
# These are added after app.urls to allow manual overrides
metadata_patterns = metadata.get_urlpatterns()
if metadata_patterns:
    urlpatterns += metadata_patterns