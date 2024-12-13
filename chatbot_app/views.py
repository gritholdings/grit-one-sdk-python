from rest_framework import viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from .models import Prompt
from .serializers import PromptSerializer
from .llm import chatbot_app
from django.http import HttpRequest


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
        thread_id = chatbot_app.create_new_thread(
            session_key=request.session.session_key
        )
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
        file = request.FILES['file']
        file_path = f'.tmp/{file.name}'

        # Determine content type
        # content_type, _ = mimetypes.guess_type(file.name)
        # if not content_type:
        #     content_type = 'application/octet-stream'

        with open(file_path, 'wb+') as destination:
            for chunk in file.chunks():
                destination.write(chunk)

        # Attach file to thread using chatbot application
        file_info = chatbot_app.attach_file_to_thread(
            session_key=request.session.session_key,
            thread_id=thread_id,
            file_path=file_path,
            file_name=file.name
        )

        return Response({
            'file_path': file_path,
            'thread_id': thread_id,
            'file_info': file_info
        }, status=status.HTTP_200_OK)

    except Exception as e:
        return Response(
            {'error': f'Failed to upload and attach file: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )