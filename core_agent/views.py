from django.http import JsonResponse
from django.contrib.admin.views.decorators import staff_member_required
from core_agent.knowledge_base import KnowledgeBaseClient
from app import settings as app_settings


@staff_member_required
def knowledge_base_webhook(request):
    kb_client = KnowledgeBaseClient()
    response = kb_client.sync_data_sources_to_vector_store()
    return JsonResponse(response)