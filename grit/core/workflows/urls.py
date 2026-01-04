"""
URL patterns for workflow API.
"""
from django.urls import path
from grit.core.workflows import views

urlpatterns = [
    path('', views.list_workflows, name='workflow_list'),
    path('<str:workflow_id>/', views.get_workflow, name='workflow_detail'),
    path('<str:workflow_id>/run/', views.run_workflow, name='workflow_run'),
]
