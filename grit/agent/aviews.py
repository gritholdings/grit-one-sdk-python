from asgiref.sync import sync_to_async
from django.http import HttpRequest, StreamingHttpResponse
from adrf.decorators import api_view
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import permission_classes
from rest_framework import status
from .store import MemoryStoreService
from .models import Agent
from .utils import save_uploaded_file


@api_view(['POST'])
@permission_classes([IsAuthenticated])
async def threads_runs(request: HttpRequest):
    """
    Threads runs Agent
    Processes chat messages for a specific thread with async streaming.
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
        # Check if there's a stored agent for this thread
        memory_store_service = MemoryStoreService()
        user_id = str(user.id)
        stored_agent_id = await sync_to_async(memory_store_service.get_current_agent_id)(user_id, thread_id)
        
        # If there's a stored agent id, try to use it
        effective_model_id = stored_agent_id if stored_agent_id else model_id
        
        agent_detail = await sync_to_async(Agent.objects.get_agent)(agent_id=effective_model_id)
        if not agent_detail:
            return Response(
                {'error': f'Model with ID {effective_model_id} not found.'},
                status=status.HTTP_404_NOT_FOUND
            )
        agent_config = await sync_to_async(agent_detail.get_config)()
        agent_class = await sync_to_async(Agent.objects.get_agent_class)(
            agent_class_str=agent_config.agent_class,
            model_name=agent_config.model_name
        )
        if not agent_class:
            return Response(
                {'error': f'Model class for {effective_model_id} not found.'},
                status=status.HTTP_404_NOT_FOUND
            )
        # Must use create because there is async in init
        chat_agent = await agent_class.create(config=agent_config, request=request)
        
        # Create an async generator to stream responses
        async def token_generator():
            try:
                async for token in chat_agent.process_chat(
                    user=user,
                    thread_id=thread_id,
                    new_message=message,
                ):
                    yield token
            except Exception as e:
                # If something breaks mid-stream:
                yield f"\n[Stream Error]: {str(e)}\n"
            finally:
                # Clean up memory store connection
                await sync_to_async(memory_store_service.close)()
                
        # Use Django's async streaming response
        return StreamingHttpResponse(
            token_generator(), 
            status=200, 
            content_type='text/event-stream'
        )
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
async def upload_files(request: HttpRequest) -> Response:
    """
    Uploads files and attaches them to a specific thread in the chatbot.
    
    Required parameters:
    - file: The file to upload
    - thread_id: The ID of the thread to attach the file to
    """
    user = request.user
    # Validate required parameters
    if 'file' not in request.FILES:
        return Response(
            {'error': 'File is required'},
            status=status.HTTP_400_BAD_REQUEST
        )

    thread_id = request.data.get('thread_id')
    if not thread_id:
        return Response(
            {'error': 'Thread ID is required'},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        # Save the file and get the original filename
        uploaded_file = request.FILES['file']
        original_filename = uploaded_file.name
        file_path = await sync_to_async(save_uploaded_file)(request.FILES, file_field_name='file')    

        # Refresh the vector store after uploading the file
        first_agent = await sync_to_async(lambda: Agent.objects.all().first())()
        if not first_agent:
            return Response(
                {'error': 'No agents available. Please configure an agent first.'},
                status=status.HTTP_404_NOT_FOUND
            )
        model_id = str(first_agent.id)
        agent_detail = await sync_to_async(Agent.objects.get_agent)(agent_id=model_id)
        if not agent_detail:
            return Response(
                {'error': f'Model with ID {model_id} not found.'},
                status=status.HTTP_404_NOT_FOUND
            )
        agent_config = await sync_to_async(agent_detail.get_config)()
        agent_class = await sync_to_async(Agent.objects.get_agent_class)(
            agent_class_str=agent_config.agent_class,
            model_name=agent_config.model_name
        )
        if not agent_class:
            return Response(
                {'error': f'Model class for {model_id} not found.'},
                status=status.HTTP_404_NOT_FOUND
            )
        chat_agent = await sync_to_async(agent_class)(config=agent_config, request=request)
        async def token_generator():
            try:
                async for token in chat_agent.process_chat(
                    user=user,
                    thread_id=thread_id,
                    new_message=file_path,
                    data_type='image',
                    file_metadata={'filename': original_filename}
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
            {'error': f'Failed to upload and attach file: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )