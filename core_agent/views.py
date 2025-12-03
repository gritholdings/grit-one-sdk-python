import uuid
from asgiref.sync import sync_to_async
from django.http import JsonResponse, HttpRequest, StreamingHttpResponse
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from rest_framework import status
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from .knowledge_base import KnowledgeBaseClient
from .models import Agent
from .store import MemoryStoreService
from .mcp_server import mcp_registry
from .settings import agent_settings


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_thread(request: HttpRequest) -> Response:
    """
    Creates a new thread for chat conversations.
    """
    try:
        thread_id = str(uuid.uuid4())
        return Response(
            {'thread_id': thread_id},
            status=status.HTTP_201_CREATED
        )
    except Exception as e:
        return Response(
            {'error': f'Failed to create thread: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST', 'DELETE'])
@permission_classes([IsAuthenticated])
def thread_detail(request: HttpRequest) -> Response:
    """
    Handles thread operations:
    - POST: Returns the details of a specific thread
    - DELETE: Deletes a specific thread
    """
    thread_id = request.data.get('thread_id')
    user_id = str(request.user.id)
    
    if not thread_id:
        return Response(
            {'error': 'Thread ID is required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    memory_store_service = MemoryStoreService()
    namespace = ("memories", user_id)
    
    if request.method == 'POST':
        # Handle getting thread details
        raw_memory = memory_store_service.get_memory(namespace, thread_id)
        if not raw_memory:
            return Response(
                {'error': 'Thread not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        conversation_history = raw_memory.value.get('conversation_history', [])
        messages = []

        for message in conversation_history:
            # Handle both old string format and new dict format
            if isinstance(message, dict):
                # New structured format
                role = message.get('role')
                content = message.get('content')
                metadata = message.get('metadata', {})
                
                # For user_image role, include filename in display
                if role == 'user_image' and metadata.get('filename'):
                    messages.append({
                        'role': role,
                        'content': f"[File uploaded: {metadata['filename']}]",
                        'metadata': metadata
                    })
                else:
                    messages.append({
                        'role': role,
                        'content': content,
                        'metadata': metadata
                    })
            else:
                # Old string format
                role, content = message.split(',', 1)
                messages.append({
                    'role': role,
                    'content': content,
                })

        return Response(
            {'messages': messages},
            status=status.HTTP_200_OK
        )
    
    elif request.method == 'DELETE':
        # Handle deleting thread
        try:
            success = memory_store_service.delete_memory(namespace, thread_id)
            
            if success:
                return Response(
                    {"success": True, "message": "Thread deleted successfully"},
                    status=status.HTTP_200_OK
                )
            else:
                return Response(
                    {"success": False, "error": "Thread not found"},
                    status=status.HTTP_404_NOT_FOUND
                )
                
        except Exception as e:
            # Log the error for debugging
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error deleting thread {thread_id} for user {user_id}: {str(e)}")
            
            return Response(
                {"success": False, "error": "Failed to delete thread"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def threads_runs(request: HttpRequest):
    """
    Processes chat messages for a specific thread.
    """
    message = request.data.get('message')
    thread_id = request.data.get('thread_id')
    model_id = request.data.get('model_id')
    user = request.user

    # Validate required parameters
    if not message:
        return Response(
            {'error': 'Message is required'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # thread_id must be provided
    if not thread_id:
        return Response(
            {'error': 'Thread ID is required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    if not model_id:
        return Response(
            {'error': 'Model ID is required'},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        agent_detail = Agent.objects.get_agent(agent_id=model_id)
        if not agent_detail:
            return Response(
                {'error': f'Model with ID {model_id} not found.'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check if user has access to this agent
        # If agent has an account, verify user belongs to that account
        if hasattr(agent_detail, 'account') and agent_detail.account:
            from core_sales.models import Contact
            try:
                contact = Contact.objects.get(user=user) # pylint: disable=all
                if contact.account != agent_detail.account:
                    return Response(
                        {'error': 'You do not have permission to access this agent.'},
                        status=status.HTTP_403_FORBIDDEN
                    )
            except Contact.DoesNotExist:
                return Response(
                    {'error': 'You do not have permission to access this agent.'},
                    status=status.HTTP_403_FORBIDDEN
                )
        
        agent_config = agent_detail.get_config()
        agent_class = Agent.objects.get_agent_class(agent_class_str=agent_config.agent_class)
        if not agent_class:
            return Response(
                {'error': f'Model class for {model_id} not found.'},
                status=status.HTTP_404_NOT_FOUND
            )
        chat_agent = agent_class(config=agent_config, request=request)
        def token_generator():
            try:
                for token in chat_agent.process_chat(
                    user=user,
                    thread_id=thread_id,
                    new_message=message,
                ):
                    yield token
            except Exception as e:
                # If something breaks mid-stream:
                yield f"\n[Stream Error]: {str(e)}\n"
        streaming_response = StreamingHttpResponse(token_generator(), status=200, content_type='text/plain')
        streaming_response['Cache-Control'] = 'no-cache'
        return streaming_response
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
def models_list(request: HttpRequest) -> Response:
    """
    Models list Agent
    Returns a list of available models.
    """
    user = request.user
    agent_config_tag = user.metadata.get('agent_config_tag', '') if user.is_authenticated else ''
    agent_list_response = Agent.objects.get_user_agents(user=user, agent_config_tag=agent_config_tag)
    agent_list = [agent.dict() for agent in agent_list_response]
    return Response({
        'models': agent_list
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
def threads_list(request: HttpRequest) -> Response:
    user_id = str(request.user.id)
    memory_store_service = MemoryStoreService()
    raw_memories = memory_store_service.list_memories(("memories", user_id))
    memories = []

    for raw_memory in raw_memories:
        # Extract messages for this memory thread
        conversation_history = raw_memory.value.get('conversation_history', [])
        title = ' - '

        for message in conversation_history:
            # Handle both old string format and new dict format
            if isinstance(message, dict):
                # New structured format
                role = message.get('role')
                content = message.get('content', '')
                metadata = message.get('metadata', {})
                
                if role == 'user':
                    # Use the first user text message as title
                    title = content
                    break
                elif role == 'user_image' and metadata.get('filename'):
                    # Skip file uploads but could show filename if desired
                    continue
            else:
                # Old string format
                role, content = message.split(',', 1)
                if role == 'user':
                    if content.startswith('base64'):
                        # Skip base64 messages
                        continue
                    # Use the first non-base64 message as title
                    title = content
                    break

        memories.append({
            'id': raw_memory.key,
            'title': title,
        })

    return Response(
        {'memories': memories},
        status=status.HTTP_200_OK
    )


@login_required
def chat_view(request, thread_id=None):
    """
    Renders the chat interface for a specific thread or new chat.
    Mounts the AppChat React component via data-react-component.
    If thread_id is None, the React component will create a new thread.
    """
    return render(request, 'agent/chat.html', {
        'thread_id': thread_id or '',
        'disable_attachment_ui_button': agent_settings.DISABLE_ATTACHMENT_UI_BUTTON,
    })


@staff_member_required
def knowledge_base_webhook(request):
    kb_client = KnowledgeBaseClient()
    response = kb_client.sync_data_sources_to_vector_store()
    return JsonResponse(response)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mcp_query(request: HttpRequest) -> Response:
    """
    MCP (Model Context Protocol) endpoint for querying registered Django models.

    This endpoint allows internal AI agents to perform read-only queries on
    registered models with proper authentication and authorization.

    Request body:
        {
            "model": "Account",           # Model name (required)
            "operation": "list",          # Operation: list, retrieve, search (required)
            "params": {                   # Operation-specific parameters (optional)
                "filters": {"name__icontains": "test"},
                "limit": 50,
                "pk": "uuid-here",
                "query": "search term",
                "search_fields": ["name", "description"]
            }
        }

    Returns:
        JSON response with query results or error message

    Security:
        - Requires authentication (Django session)
        - Enforces read-only operations
        - Respects APP_METADATA_SETTINGS permissions
        - Only exposes explicitly registered models
    """
    from django.http import Http404
    from core.utils.permissions import check_group_permission, check_profile_permission
    from core.utils.case_conversion import camel_to_snake
    from app.settings import APP_METADATA_SETTINGS

    # Extract request parameters
    model_name = request.data.get('model')
    operation = request.data.get('operation')
    params = request.data.get('params', {})

    # Validate required parameters
    if not model_name:
        return Response(
            {'error': 'Model name is required'},
            status=status.HTTP_400_BAD_REQUEST
        )

    if not operation:
        return Response(
            {'error': 'Operation is required'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Validate operation is read-only
    allowed_operations = ['list', 'retrieve', 'search', 'list_tools']
    if operation not in allowed_operations:
        return Response(
            {'error': f'Invalid operation. Allowed: {", ".join(allowed_operations)}'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Special operation: list available tools
    if operation == 'list_tools':
        tools = mcp_registry.list_available_tools()
        return Response({'tools': tools}, status=status.HTTP_200_OK)

    # Get the toolset for this model
    toolset_class, model_class = mcp_registry.get_by_name(model_name)

    if not toolset_class:
        return Response(
            {'error': f'Model "{model_name}" is not registered for MCP access'},
            status=status.HTTP_404_NOT_FOUND
        )

    # Check permissions using existing permission system
    model_name_snake = camel_to_snake(model_class.__name__)

    # Check group-based permissions
    has_group_permission = check_group_permission(
        user=request.user,
        model_name=model_name_snake,
        settings=APP_METADATA_SETTINGS
    )

    # Check profile-based permissions (read access)
    has_profile_permission = check_profile_permission(
        user=request.user,
        model_name=model_name_snake,
        permission_type='allow_read',
        settings=APP_METADATA_SETTINGS
    )

    # Use OR logic: if either permission grants access, allow it
    if not (has_group_permission or has_profile_permission):
        return Response(
            {'error': f'You do not have permission to access {model_name}'},
            status=status.HTTP_403_FORBIDDEN
        )

    # Instantiate the toolset with the request context
    try:
        toolset = toolset_class(request=request)
    except Exception as e:
        return Response(
            {'error': f'Failed to initialize toolset: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    # Execute the requested operation
    try:
        if operation == 'list':
            filters = params.get('filters')
            limit = params.get('limit')
            result = toolset.list(filters=filters, limit=limit)

        elif operation == 'retrieve':
            pk = params.get('pk')
            if not pk:
                return Response(
                    {'error': 'Primary key (pk) is required for retrieve operation'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            result = toolset.retrieve(pk=pk)

        elif operation == 'search':
            query = params.get('query')
            if not query:
                return Response(
                    {'error': 'Query parameter is required for search operation'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            search_fields = params.get('search_fields')
            limit = params.get('limit')
            result = toolset.search(query=query, search_fields=search_fields, limit=limit)

        return Response(result, status=status.HTTP_200_OK)

    except Http404 as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_404_NOT_FOUND
        )
    except ValueError as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        # Log the error for debugging
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"MCP query error: {str(e)}", exc_info=True)

        return Response(
            {'error': f'Query failed: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )