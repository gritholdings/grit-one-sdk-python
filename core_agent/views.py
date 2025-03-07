from django.http import JsonResponse
from django.contrib.admin.views.decorators import staff_member_required
from core_agent.knowledge_base import KnowledgeBaseClient
from app import settings as app_settings


@staff_member_required
def knowledge_base_webhook(request):
    bucket_name = app_settings.KB_AWS_S3_BUCKET_NAME
    kb_client = KnowledgeBaseClient(bucket_name=bucket_name)
    response = kb_client.upload_github_folder_to_s3(
        github_owner=app_settings.KB_GITHUB_OWNER,
        github_repo=app_settings.KB_GITHUB_REPO,
        github_folder=app_settings.KB_GITHUB_FOLDER,
        github_branch='main'
    )
    return JsonResponse(response)