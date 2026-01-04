"""
Core Urls
"""
from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView
from home import views as home_views
from grit.core import views as core_views
from grit.core.metadata import metadata
from grit.core.metadata.autodiscover import autodiscover
from grit.core.shortcuts import auth_redirect
from grit.core.workflows import views as workflow_views

# Autodiscover metadata registrations from all apps
autodiscover()

urlpatterns = [
    # Workflow API endpoints
    path('api/workflows/', include('grit.core.workflows.urls')),
    # Workflow page views
    path('workflows/', workflow_views.workflow_list_page, name='workflow_list_page'),
    path('workflows/<str:workflow_id>/', workflow_views.workflow_detail_page, name='workflow_detail_page'),
    path('auth/', include('grit.auth.urls')),
    path('admin/', admin.site.urls),
    path('onboarding/', RedirectView.as_view(pattern_name='onboarding', permanent=False), {'step': 1}, name='onboarding_default'),
    path('onboarding/<int:step>/', home_views.onboarding, name='onboarding'),
    path('onboarding/save/', home_views.save_onboarding_progress, name='save_onboarding_progress'),
    path('profile/', home_views.profile, name='profile'),
    path('app/<str:app_name>/', core_views.app_specific_view, name='app_specific'),
    path('app/', core_views.app_view, name='app'),
    path('', auth_redirect('app', 'home'), name='index'),
    path('', include('app.urls')),
]

# Append auto-generated metadata URLs
# These are added after app.urls to allow manual overrides
metadata_patterns = metadata.get_urlpatterns()
if metadata_patterns:
    urlpatterns += metadata_patterns