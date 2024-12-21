import os
import uuid
from rest_framework import viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from .models import Prompt
from .serializers import PromptSerializer
from .llm import CustomerSupportAgent
from django.http import HttpRequest
from core_agent.chroma import ChromaService


class PromptView(viewsets.ModelViewSet):
    queryset = Prompt.objects.all()
    serializer_class = PromptSerializer


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

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def threads_runs(request: HttpRequest) -> Response:
    """
    Processes chat messages for a specific thread.
    """
    message = request.data.get('message')
    thread_id = request.data.get('thread_id')

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

    try:
        chatbot_app = CustomerSupportAgent()
        response = chatbot_app.process_chat(
            session_key=request.session.session_key,
            thread_id=thread_id,
            new_message=message
        )
        return Response(response, status=status.HTTP_200_OK)
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def upload_files(request: HttpRequest) -> Response:
    """
    Uploads files and attaches them to a specific thread in the chatbot.
    
    Required parameters:
    - file: The file to upload
    - thread_id: The ID of the thread to attach the file to
    """
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
        # Save the file
        # Create .tmp directory if it doesn't exist
        tmp_dir = '.tmp'
        os.makedirs(tmp_dir, exist_ok=True)
        file = request.FILES['file']
        file_path = os.path.join(tmp_dir, file.name)

        # Save file to disk
        with open(file_path, 'wb+') as destination:
            for chunk in file.chunks():
                destination.write(chunk)

        # Refresh the vector store after uploading the file
        chroma_service = ChromaService()
        chroma_service.upload_and_vectorize_pdf_for_thread(thread_id, file_path)

        return Response({
            'file_path': file_path,
            'file_name': file.name,
            'thread_id': thread_id,
        }, status=status.HTTP_200_OK)

    except Exception as e:
        return Response(
            {'error': f'Failed to upload and attach file: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )