"""
API views for workflow execution.

Provides endpoints for triggering and managing workflows.
"""
import json
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required

from app import settings
from grit.core.workflows.engine import WorkflowEngine
from grit.core.utils.case_conversion import convert_keys_to_camel_case, resolve_urls_in_app_metadata
from grit.core.utils.permissions import (
    filter_app_metadata_by_user_groups,
    filter_app_metadata_by_user_profile,
    merge_filtered_settings,
)


def get_workflows_config():
    """Get workflows configuration from settings."""
    return settings.APP_METADATA_SETTINGS.get('WORKFLOWS', {})


@csrf_exempt
@require_http_methods(["POST"])
def run_workflow(request, workflow_id: str):
    """
    Execute a workflow by its ID.

    POST /api/workflows/<workflow_id>/run

    Returns:
        JsonResponse with execution result:
        {
            "success": true/false,
            "workflow_id": "workflow_1",
            "workflow_name": "Workflow 1",
            "wf": { ... workflow context data ... },
            "nodes": { ... node contexts ... },
            "error": "..." (only if success=false)
        }
    """
    workflows = get_workflows_config()

    if workflow_id not in workflows:
        return JsonResponse(
            {"error": f"Workflow '{workflow_id}' not found"},
            status=404
        )

    workflow_config = workflows[workflow_id]
    engine = WorkflowEngine(workflow_id=workflow_id, config=workflow_config)
    result = engine.run()

    status_code = 200 if result["success"] else 500
    return JsonResponse(result, status=status_code)


@require_http_methods(["GET"])
def list_workflows(request):
    """
    List all available workflows.

    GET /api/workflows

    Returns:
        JsonResponse with list of workflows:
        {
            "workflows": [
                {
                    "id": "workflow_1",
                    "name": "Workflow 1",
                    "node_count": 2,
                    "edge_count": 1
                },
                ...
            ]
        }
    """
    workflows = get_workflows_config()

    workflow_list = []
    for workflow_id, config in workflows.items():
        workflow_list.append({
            "id": workflow_id,
            "name": config.get("meta", {}).get("name", workflow_id),
            "node_count": len(config.get("nodes", {})),
            "edge_count": len(config.get("edges", {}))
        })

    return JsonResponse({"workflows": workflow_list})


@require_http_methods(["GET"])
def get_workflow(request, workflow_id: str):
    """
    Get details of a specific workflow.

    GET /api/workflows/<workflow_id>

    Returns:
        JsonResponse with workflow configuration
    """
    workflows = get_workflows_config()

    if workflow_id not in workflows:
        return JsonResponse(
            {"error": f"Workflow '{workflow_id}' not found"},
            status=404
        )

    return JsonResponse({
        "id": workflow_id,
        "config": workflows[workflow_id]
    })


# =============================================================================
# Page Views (for rendering React components)
# =============================================================================

def _get_app_metadata_context(request):
    """Helper to get filtered app metadata for the current user."""
    group_filtered = filter_app_metadata_by_user_groups(
        settings.APP_METADATA_SETTINGS, request.user
    )
    profile_filtered = filter_app_metadata_by_user_profile(
        settings.APP_METADATA_SETTINGS, request.user
    )
    filtered_settings = merge_filtered_settings(
        group_filtered, profile_filtered, settings.APP_METADATA_SETTINGS
    )
    return json.dumps(
        convert_keys_to_camel_case(resolve_urls_in_app_metadata(filtered_settings))
    )


@login_required
def workflow_list_page(request):
    """
    Render the workflow list page.

    GET /workflows/
    """
    context = {
        'app_metadata_settings_json': _get_app_metadata_context(request)
    }
    return render(request, 'core/workflows/workflow_list.html', context)


@login_required
def workflow_detail_page(request, workflow_id: str):
    """
    Render the workflow detail page.

    GET /workflows/<workflow_id>/
    """
    context = {
        'workflow_id': workflow_id,
        'app_metadata_settings_json': _get_app_metadata_context(request)
    }
    return render(request, 'core/workflows/workflow_detail.html', context)
