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
    return settings.APP_METADATA_SETTINGS.get('WORKFLOWS', {})
@csrf_exempt
@require_http_methods(["POST"])


def run_workflow(request, workflow_id: str):
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


def _get_app_metadata_context(request):
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
    context = {
        'app_metadata_settings_json': _get_app_metadata_context(request)
    }
    return render(request, 'core/workflows/workflow_list.html', context)
@login_required


def workflow_detail_page(request, workflow_id: str):
    context = {
        'workflow_id': workflow_id,
        'app_metadata_settings_json': _get_app_metadata_context(request)
    }
    return render(request, 'core/workflows/workflow_detail.html', context)
